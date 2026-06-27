"""
STEP file parser for simulation boundary condition selection.

Parses STEP/STP files into mesh data, extracts face groups,
and exports to GLB format for 3D visualization with face picking support.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Optional

import numpy as np
import trimesh


class FaceGroup:
    """Represents a logical face group (set of triangles forming a CAD face)."""

    def __init__(self, face_id: int, face_indices: np.ndarray, mesh: trimesh.Trimesh):
        self.face_id = face_id
        self.face_indices = face_indices  # indices into mesh.faces
        self._mesh = mesh

    @property
    def centroid(self) -> list[float]:
        centers = self._mesh.triangles_center[self.face_indices]
        areas = self._mesh.area_faces[self.face_indices]
        total_area = areas.sum()
        if total_area > 0:
            weighted = (centers * areas[:, None]).sum(axis=0) / total_area
        else:
            weighted = centers.mean(axis=0)
        return weighted.tolist()

    @property
    def area(self) -> float:
        return float(self._mesh.area_faces[self.face_indices].sum())

    @property
    def normal(self) -> list[float]:
        """Area-weighted average normal."""
        normals = self._mesh.face_normals[self.face_indices]
        areas = self._mesh.area_faces[self.face_indices]
        total_area = areas.sum()
        if total_area > 0:
            avg = (normals * areas[:, None]).sum(axis=0) / total_area
        else:
            avg = normals.mean(axis=0)
        # normalize
        length = np.linalg.norm(avg)
        if length > 0:
            avg = avg / length
        return avg.tolist()

    @property
    def triangle_count(self) -> int:
        return len(self.face_indices)

    @property
    def face_type(self) -> str:
        """Infer face type from normal variance."""
        normals = self._mesh.face_normals[self.face_indices]
        if len(normals) <= 1:
            return "planar"
        # Check variance of normals
        var = np.var(normals, axis=0).sum()
        if var < 0.001:
            return "planar"
        elif var < 0.1:
            return "curved"
        else:
            return "complex"

    def to_dict(self) -> dict:
        return {
            "face_id": self.face_id,
            "centroid": self.centroid,
            "area": round(self.area, 6),
            "normal": [round(n, 4) for n in self.normal],
            "face_type": self.face_type,
            "triangle_count": len(self.face_indices),
        }


class StepModel:
    """Parsed STEP model with face groups and mesh data."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.model_id = uuid.uuid4().hex[:12]
        self._mesh: Optional[trimesh.Trimesh] = None
        self.face_groups: list[FaceGroup] = []
        self._load()

    def _load(self):
        """Load and parse the STEP/STL/etc file.

        For STEP files: preserves CAD face boundaries by tracking which mesh
        triangles came from which original CAD geometry. Small CAD geometries
        (like end caps) become their own face groups; large ones are subdivided
        by surface normal only (no adjacency merging that causes face bleeding).
        """
        ext = Path(self.file_path).suffix.lower()

        try:
            print(f"  Loading: {Path(self.file_path).name} (format: {ext})")
        except UnicodeEncodeError:
            print(f"  Loading: model.{ext} (format: {ext})")

        try:
            if ext in (".stp", ".step"):
                self._load_step_preserving_faces()
            elif ext in (".stl",):
                self._mesh = trimesh.load(self.file_path, file_type="stl")
            elif ext in (".obj",):
                self._mesh = trimesh.load(self.file_path, file_type="obj")
            elif ext in (".glb", ".gltf"):
                self._mesh = trimesh.load(self.file_path, file_type="glb")
            else:
                self._mesh = trimesh.load(self.file_path)
        except Exception as e:
            raise ValueError(f"Failed to load {ext} file: {e}\n"
                             f"Supported: .stp, .step, .stl, .obj, .glb, .gltf, .ply\n"
                             f"Windows: pip install cascadio\n"
                             f"Linux/WSL: pip install gmsh (or: sudo apt install gmsh)")

        # Post-processing: validate
        if self._mesh is None:
            raise ValueError(f"Failed to load mesh from {self.file_path}")
        if isinstance(self._mesh, trimesh.Scene) and len(self._mesh.geometry) == 0:
            raise ValueError(f"Empty scene in {self.file_path}")
        if hasattr(self._mesh, "faces") and len(self._mesh.faces) == 0:
            raise ValueError(f"No faces found in {self.file_path}")

        # For non-STEP files, use legacy approach
        if ext not in (".stp", ".step"):
            if isinstance(self._mesh, trimesh.Scene):
                meshes = []
                for name, geom in self._mesh.geometry.items():
                    if hasattr(geom, "faces") and len(geom.faces) > 0:
                        meshes.append(geom)
                if not meshes:
                    raise ValueError("No mesh geometry found in scene")
                self._mesh = trimesh.util.concatenate(meshes)
                print(f"  Combined {len(meshes)} geometries into single mesh")

            print(f"  Loaded mesh: {len(self._mesh.vertices)} vertices, "
                  f"{len(self._mesh.faces)} faces")
            self._mesh.merge_vertices()
            self._mesh.face_normals
            self._group_faces_legacy()
        else:
            # STEP: mesh and face groups already built by _load_step_preserving_faces
            print(f"  Loaded mesh: {len(self._mesh.vertices)} vertices, "
                  f"{len(self._mesh.faces)} faces")
            # face_groups already populated

    def _load_step(self):
        """Load STEP file, trying cascadio then gmsh then OCP.

        Returns a trimesh.Scene (preferred) or Trimesh.
        """
        # Try cascadio (preserves CAD face structure best)
        try:
            import cascadio  # noqa: F401
            print("    Using cascadio backend")
            return trimesh.load(self.file_path, file_type="step")
        except ImportError:
            pass

        # Try gmsh (cross-platform)
        try:
            import gmsh  # noqa: F401
            print("    Using gmsh backend")
            return trimesh.load(self.file_path, file_type="step")
        except ImportError:
            pass

        # Try OCP (cadquery)
        try:
            import OCP  # noqa: F401
            print("    Using OCP backend")
            return trimesh.load(self.file_path, file_type="step")
        except ImportError:
            pass

        raise ImportError(
            "No STEP loader available. Install one:\n"
            "  Windows: pip install cascadio\n"
            "  Linux/WSL: pip install gmsh\n"
            "  Alternative: pip install cadquery"
        )

    def _load_step_preserving_faces(self):
        """Load STEP file preserving CAD boundaries with edge-based grouping.

        - Each CAD geometry is concatenated ONCE into a unified mesh
        - Edge-based subdivision runs per-geometry (30° dihedral threshold)
        - Face groups track GLOBAL face indices into the unified mesh
        - No geometry duplication → correct rendering and face picking
        """
        raw = self._load_step()

        if isinstance(raw, trimesh.Scene):
            geom_items = list(raw.geometry.items())
            print(f"  STEP scene: {len(geom_items)} CAD geometries")
        elif isinstance(raw, trimesh.Trimesh):
            geom_items = [("body", raw)]
        else:
            raise ValueError(f"Unexpected STEP load result type: {type(raw)}")

        # Phase 1: edge-subdivide each geometry, collect local groups
        # (group_id, geom_index, local_face_indices)
        local_groups = []  # list of (geom_idx, np.array of local face indices)
        geom_meshes = []   # cleaned geometries (one per CAD body)

        for geom_idx, (geom_name, geom) in enumerate(geom_items):
            if not hasattr(geom, "faces") or len(geom.faces) == 0:
                continue

            geom.merge_vertices()
            _ = geom.face_normals
            n_faces = len(geom.faces)
            geom_meshes.append(geom)

            sub_groups = self._subdivide_by_edges(geom, angle_threshold_deg=15)
            kept = 0
            for sub_indices in sub_groups:
                if len(sub_indices) < 2:
                    continue
                local_groups.append((geom_idx, sub_indices))
                kept += 1
            print(f"    {geom_name}: {n_faces} faces → {kept} groups "
                  f"(edge-based, {len(sub_groups)} raw)")

        if not local_groups:
            raise ValueError("No face groups extracted from STEP file")

        # Phase 2: concatenate all geometries ONCE into unified mesh
        self._mesh = trimesh.util.concatenate(geom_meshes)
        self._mesh.merge_vertices()
        self._mesh.face_normals  # ensure computed

        # Compute per-geometry face offsets into unified mesh
        geom_offsets = [0]
        for gm in geom_meshes[:-1]:
            geom_offsets.append(geom_offsets[-1] + len(gm.faces))

        # Phase 3: build FaceGroups with GLOBAL face indices
        face_groups = []
        for group_id, (geom_idx, local_indices) in enumerate(local_groups):
            global_indices = local_indices + geom_offsets[geom_idx]
            fg = FaceGroup(group_id, global_indices, self._mesh)
            face_groups.append(fg)

        # Sort by area (largest first) and re-ID
        face_groups.sort(key=lambda fg: fg.area, reverse=True)
        for i, fg in enumerate(face_groups):
            fg.face_id = i

        self.face_groups = face_groups
        print(f"  Unified mesh: {len(self._mesh.vertices)} verts, {len(self._mesh.faces)} faces, "
              f"{len(self.face_groups)} face groups")

        for fg in self.face_groups[:12]:
            n = fg.normal
            print(f"    Face {fg.face_id}: area={fg.area:.4f}, "
                  f"normal=({n[0]:.2f},{n[1]:.2f},{n[2]:.2f}), "
                  f"type={fg.face_type}, tris={fg.triangle_count}")
        if len(self.face_groups) > 12:
            print(f"    ... and {len(self.face_groups) - 12} more")

    def _subdivide_by_edges(self, mesh: "trimesh.Trimesh",
                            angle_threshold_deg: float = 30) -> list[np.ndarray]:
        """Subdivide mesh by sharp edges (棱线).

        Two adjacent faces belong to the same surface group if their dihedral
        angle is LESS than the threshold — they form a smooth continuous surface.

        Sharp edges (dihedral angle > threshold) act as boundaries between groups.
        This correctly handles:
          - Cylindrical surfaces → one continuous group (gradual normal change)
          - Planar surfaces → one group (constant normal)
          - Cube corners → split at 90° edges
          - CAD model ridges → split at sharp creases

        Returns list of face-index arrays, one per group.
        """
        normals = mesh.face_normals
        n_faces = len(normals)

        if n_faces <= 1:
            return [np.arange(n_faces, dtype=int)]

        import math
        cos_threshold = math.cos(math.radians(angle_threshold_deg))

        # Union-Find: each face starts alone
        parent = list(range(n_faces))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Build adjacency list from face adjacency edges
        # mesh.face_adjacency returns pairs of adjacent face indices
        adjacency_edges = mesh.face_adjacency  # shape (n_edges, 2)
        adjacency_unique = set()
        for a, b in adjacency_edges:
            if a < b:
                adjacency_unique.add((a, b))
            else:
                adjacency_unique.add((b, a))
        adj_list = [set() for _ in range(n_faces)]
        for a, b in adjacency_unique:
            adj_list[a].add(b)
            adj_list[b].add(a)

        # Union adjacent faces that form a smooth surface
        n_union = 0
        for a in range(n_faces):
            for b in adj_list[a]:
                if b <= a:
                    continue
                if find(a) == find(b):
                    continue
                dot = np.dot(normals[a], normals[b])
                if dot > cos_threshold:
                    union(a, b)
                    n_union += 1

        # Collect groups
        groups = {}
        for i in range(n_faces):
            root = find(i)
            groups.setdefault(root, []).append(i)

        # Filter out tiny groups (noise), merge into nearest large group
        min_size = max(1, n_faces // 500)
        large = {k: v for k, v in groups.items() if len(v) >= min_size}
        small = {k: v for k, v in groups.items() if len(v) < min_size}

        for sk, sfaces in small.items():
            if not large:
                large[sk] = sfaces
                continue
            s_normal = np.array(normals[sfaces].mean(axis=0), copy=True)
            s_normal /= np.linalg.norm(s_normal) + 1e-10
            best_k = max(large.keys(),
                        key=lambda k: abs(np.dot(s_normal,
                                        np.array(normals[large[k][0]], copy=True))))
            large[best_k].extend(sfaces)

        result = [np.array(v, dtype=int) for v in large.values()]
        print(f"      Edge-based: {n_faces} faces → {len(result)} groups "
              f"(threshold={angle_threshold_deg}°, {n_union} unions, "
              f"{n_faces - n_union} edges kept)")
        return result

    def _group_faces_legacy(self):
        """Legacy face grouping for non-STEP files (STL, OBJ, etc.).

        Groups triangle faces by normal similarity + adjacency.
        """
        self._group_faces()  # call the old implementation

    def _group_faces(self):
        """Group triangle faces into logical CAD faces by normal + adjacency."""
        adjacency = self._mesh.face_adjacency  # (n_edges, 2) pairs of adjacent face indices
        normals = self._mesh.face_normals
        n_faces = len(self._mesh.faces)

        # Build adjacency list
        adj_list: list[set[int]] = [set() for _ in range(n_faces)]
        for a, b in adjacency:
            adj_list[a].add(b)
            adj_list[b].add(a)

        # Union-Find for grouping
        parent = list(range(n_faces))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Group by normal similarity + adjacency (BFS-inspired)
        normal_threshold = 0.95  # cos(angle) threshold for "same direction"

        for i in range(n_faces):
            for j in adj_list[i]:
                if find(i) == find(j):
                    continue
                dot = np.dot(normals[i], normals[j])
                if dot > normal_threshold:
                    union(i, j)

        # Collect groups
        groups: dict[int, list[int]] = {}
        for i in range(n_faces):
            root = find(i)
            groups.setdefault(root, []).append(i)

        # Filter tiny groups (noise) - merge into nearest large group
        min_group_size = max(1, n_faces // 500)  # at least 1, at most 0.2% of faces
        large_groups = {k: v for k, v in groups.items() if len(v) >= min_group_size}
        tiny_groups = {k: v for k, v in groups.items() if len(v) < min_group_size}

        # Merge tiny groups into nearest large group by normal similarity
        for tiny_root, tiny_faces in tiny_groups.items():
            if not large_groups:
                large_groups[tiny_root] = tiny_faces
                continue
            tiny_normal = normals[tiny_faces].mean(axis=0)
            tiny_normal /= np.linalg.norm(tiny_normal)
            best_root = max(large_groups, key=lambda r: abs(
                np.dot(tiny_normal, normals[large_groups[r][0]])
            ))
            large_groups[best_root].extend(tiny_faces)

        # Create FaceGroup objects, sorted by area (largest first)
        face_group_objects = []
        for root, face_indices in large_groups.items():
            indices = np.array(face_indices, dtype=int)
            fg = FaceGroup(len(face_group_objects), indices, self._mesh)
            face_group_objects.append(fg)

        face_group_objects.sort(key=lambda fg: fg.area, reverse=True)
        # Re-assign IDs after sorting
        for i, fg in enumerate(face_group_objects):
            fg.face_id = i

        self.face_groups = face_group_objects
        print(f"  Grouped into {len(self.face_groups)} face groups")

        # Print summary
        for fg in self.face_groups[:10]:
            n = fg.normal
            print(f"    Face {fg.face_id}: area={fg.area:.4f}, "
                  f"normal=({n[0]:.2f},{n[1]:.2f},{n[2]:.2f}), "
                  f"type={fg.face_type}, triangles={fg.triangle_count}")
        if len(self.face_groups) > 10:
            print(f"    ... and {len(self.face_groups) - 10} more")

    def export_glb(self, output_path: str):
        """Export as GLB with per-group sub-meshes extracted from unified mesh.

        Each group gets its own sub-mesh with dedicated vertices → crisp color
        boundaries, no blending between groups. trimesh.util.concatenate
        preserves sub-mesh face order for correct fgmap construction.
        """
        np.random.seed(42)

        sub_meshes = []
        sub_info = []  # (group_id, tri_count)

        for fg in self.face_groups:
            hue = fg.face_id / max(1, len(self.face_groups))
            r = int(255 * (0.5 + 0.5 * np.sin(2 * np.pi * hue)))
            g = int(255 * (0.5 + 0.5 * np.sin(2 * np.pi * hue + 2.094)))
            b = int(255 * (0.5 + 0.5 * np.sin(2 * np.pi * hue + 4.189)))

            sub = self._mesh.submesh([fg.face_indices], append=True)
            vc = np.zeros((len(sub.vertices), 4), dtype=np.uint8)
            vc[:, :3] = [r, g, b]
            vc[:, 3] = 255
            sub.visual.vertex_colors = vc
            sub_meshes.append(sub)
            sub_info.append((fg.face_id, len(sub.faces)))

        combined = trimesh.util.concatenate(sub_meshes)
        combined.export(output_path, file_type="glb")

        # fgmap: triangle index in concatenated GLB → group ID
        total = len(combined.faces)
        fgmap = [-1] * total
        offset = 0
        for gid, n in sub_info:
            for t in range(n):
                fgmap[offset + t] = gid
            offset += n

        unmapped = fgmap.count(-1)
        map_path = output_path.replace(".glb", "_fgmap.json")
        with open(map_path, "w") as f:
            json.dump({
                "total_triangles": total,
                "group_count": len(self.face_groups),
                "map": fgmap,
            }, f)
        print(f"  Exported GLB: {len(sub_meshes)} sub-meshes, {total} tris"
              + (f", {unmapped} unmapped" if unmapped else ""))

    def face_id_from_vertex_color(self, color: tuple[int, int, int]) -> int:
        """Map a vertex color back to the closest face group ID."""
        np.random.seed(42)
        best_id = 0
        best_dist = float("inf")
        for fg in self.face_groups:
            hue = fg.face_id / max(1, len(self.face_groups))
            r = int(255 * (0.5 + 0.5 * np.sin(2 * np.pi * hue)))
            g = int(255 * (0.5 + 0.5 * np.sin(2 * np.pi * hue + 2.094)))
            b = int(255 * (0.5 + 0.5 * np.sin(2 * np.pi * hue + 4.189)))
            dist = (color[0] - r) ** 2 + (color[1] - g) ** 2 + (color[2] - b) ** 2
            if dist < best_dist:
                best_dist = dist
                best_id = fg.face_id
        return best_id

    def get_summary(self) -> dict:
        """Return model summary for the API."""
        return {
            "model_id": self.model_id,
            "file_name": Path(self.file_path).name,
            "vertex_count": len(self._mesh.vertices),
            "face_count": len(self._mesh.faces),
            "face_groups": [fg.to_dict() for fg in self.face_groups],
            "bounding_box": {
                "min": self._mesh.bounds[0].tolist(),
                "max": self._mesh.bounds[1].tolist(),
                "center": self._mesh.centroid.tolist(),
                "extents": self._mesh.extents.tolist(),
            },
        }


# Global model cache
_model_cache: dict[str, StepModel] = {}


def parse_file(file_path: str) -> dict:
    """Parse a STEP file and return summary. Caches the model."""
    model = StepModel(file_path)
    _model_cache[model.model_id] = model
    return model.get_summary()


def export_model_glb(model_id: str, output_dir: str) -> str:
    """Export a parsed model to GLB format. Returns output path."""
    model = _model_cache.get(model_id)
    if model is None:
        raise ValueError(f"Model {model_id} not found")

    output_path = os.path.join(output_dir, f"{model_id}.glb")
    model.export_glb(output_path)
    return output_path


def get_model(model_id: str) -> Optional[StepModel]:
    """Get cached model by ID."""
    return _model_cache.get(model_id)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python step_parser.py <file.stp>")
        sys.exit(1)

    filepath = sys.argv[1]
    summary = parse_file(filepath)
    print("\nModel Summary:")
    print(json.dumps(summary, indent=2, default=str))
