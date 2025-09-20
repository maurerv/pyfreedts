from typing import Tuple
from pathlib import Path

import numpy as np

from ._core import Mesh as _Mesh
from .utils import suppress_stdout_stderr


class Mesh:
    """
    A Python interface for FreeDTS Mesh instances.

    Parameters
    ----------
    filename : str or Path
        Path to the mesh file to load

    Attributes
    ----------
    vertices : np.ndarray
        Vertex positions as (N, 3) array
    triangles : np.ndarray
        Triangle connectivity as (M, 3) array of vertex indices
    inclusions : np.ndarray
        Vertex inclusions as (k,) array of vertex indices
    """

    def __init__(self, filename: str | Path):
        """Initialize mesh from file."""
        filename = str(filename)
        if not Path(filename).exists():
            raise FileNotFoundError(f"Mesh file not found: {filename}")

        with suppress_stdout_stderr():
            self._mesh = _Mesh(filename)

    @property
    def vertices(self) -> np.ndarray:
        """Get vertex positions as (N, 3) numpy array."""
        return self._mesh.vertices

    @property
    def triangles(self) -> np.ndarray:
        """Get triangle connectivity as (M, 3) numpy array."""
        return self._mesh.triangles

    @property
    def inclusions(self):
        """Get inclusions as (k,) vertex index numpy array."""
        inclusions, _ = self.get_vertex_inclusion_mapping()
        return inclusions

    def get_curvatures(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get principal curvatures for all vertices.

        Returns
        -------
        k1 : np.ndarray
            First principal curvature for each vertex
        k2 : np.ndarray
            Second principal curvature for each vertex
        """
        curvatures = self._mesh.get_vertex_curvatures()
        return curvatures[:, 0], curvatures[:, 1]

    def get_mean_curvatures(self) -> np.ndarray:
        """
        Get mean curvature (k1 + k2) / 2 for all vertices.

        Returns
        -------
        np.ndarray
            Mean curvature for each vertex
        """
        k1, k2 = self.get_curvatures()
        return (k1 + k2) / 2

    def get_gaussian_curvatures(self) -> np.ndarray:
        """
        Get Gaussian curvature (k1 * k2) for all vertices.

        Returns
        -------
        np.ndarray
            Gaussian curvature for each vertex
        """
        k1, k2 = self.get_curvatures()
        return k1 * k2

    def get_vertex_normals(self) -> np.ndarray:
        """
        Get vertex normals.

        Returns
        -------
        np.ndarray
            Vertex normals as (N, 3) array
        """
        return self._mesh.get_vertex_normals()

    def get_vertex_areas(self) -> np.ndarray:
        """
        Get vertex areas.

        Returns
        -------
        np.ndarray
            Area associated with each vertex
        """
        return self._mesh.get_vertex_areas()

    def get_vertex_inclusion_mapping(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get mapping of vertices to their inclusion types.

        Only returns vertices that actually have inclusions.

        Returns
        -------
        vertex_ids : np.ndarray
            Array of vertex IDs that have inclusions
        inclusion_type_ids : np.ndarray
            Array of inclusion type IDs corresponding to each vertex
        """
        return self._mesh.get_vertex_inclusion_mapping()

    def __repr__(self) -> str:
        n_v = self.vertices.shape[0]
        n_t = self.triangles.shape[0]
        n_i = self.inclusions.shape[0]
        return f"Mesh(vertices={n_v}, triangles={n_t}, inclusions={n_i})"
