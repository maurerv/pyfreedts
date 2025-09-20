#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <memory>

#include "pyfreedts/_cpp/dts_src/MESH.h"
#include "pyfreedts/_cpp/dts_src/CreateMashBluePrint.h"
#include "pyfreedts/_cpp/dts_src/CurvatureByShapeOperatorType1.h"

namespace py = pybind11;

MeshBluePrint CreateBlueprintFromArrays(
    py::array_t<double> vertices,
    py::array_t<int> triangles,
    py::array_t<int> inclusions = py::array_t<int>(),
    py::array_t<double> inclusion_directions = py::array_t<double>(),
    py::array_t<double> box_size = py::array_t<double>(),
    py::array_t<int> vertex_domains = py::array_t<int>()
) {
    MeshBluePrint blueprint;

    auto vert_buf = vertices.request();
    auto tri_buf = triangles.request();

    if (vert_buf.ndim != 2 || vert_buf.shape[1] != 3)
        throw std::runtime_error("Vertices must be a (N, 3) array");
    if (tri_buf.ndim != 2 || tri_buf.shape[1] != 3)
        throw std::runtime_error("Triangles must be a (M, 3) array");

    if (box_size.size() > 0) {
        auto box_buf = box_size.request();
        if (box_buf.size != 3)
            throw std::runtime_error("Box size must be a 3-element array");
        double* box_ptr = static_cast<double*>(box_buf.ptr);
        for (int i = 0; i < 3; ++i) blueprint.simbox(i) = box_ptr[i];
    } else {
        blueprint.simbox(0) = blueprint.simbox(1) = blueprint.simbox(2) = 1.0;
    }

    double* vert_ptr = static_cast<double*>(vert_buf.ptr);
    int* dom_ptr = vertex_domains.size() > 0 ? static_cast<int*>(vertex_domains.request().ptr) : nullptr;

    int n_verts = vert_buf.shape[0];
    blueprint.bvertex.reserve(n_verts);
    for (int i = 0; i < n_verts; ++i) {
        Vertex_Map v = {vert_ptr[i*3], vert_ptr[i*3+1], vert_ptr[i*3+2],
                        i, dom_ptr ? dom_ptr[i] : 0, true};
        blueprint.bvertex.push_back(v);
    }

    int* tri_ptr = static_cast<int*>(tri_buf.ptr);
    int n_tris = tri_buf.shape[0];
    blueprint.btriangle.reserve(n_tris);
    for (int i = 0; i < n_tris; ++i) {
        int v1 = tri_ptr[i*3], v2 = tri_ptr[i*3+1], v3 = tri_ptr[i*3+2];

        if (v1 >= n_verts || v2 >= n_verts || v3 >= n_verts || v1 < 0 || v2 < 0 || v3 < 0)
            throw std::runtime_error("Triangle references invalid vertex index");
        if (v1 == v2 || v1 == v3 || v2 == v3)
            throw std::runtime_error("Degenerate triangle: vertices must be different");
        Triangle_Map t = {i, v1, v2, v3};
        blueprint.btriangle.push_back(t);
    }

    if (inclusions.size() > 0) {
        auto inc_buf = inclusions.request();
        auto dir_buf = inclusion_directions.request();

        if (inc_buf.ndim != 2 || inc_buf.shape[1] != 2 || dir_buf.ndim != 2 ||
            dir_buf.shape[1] != 2 || dir_buf.shape[0] != inc_buf.shape[0])
            throw std::runtime_error("Inclusions must be (K,2) and directions must be (K,2) with matching K");

        int* inc_ptr = static_cast<int*>(inc_buf.ptr);
        double* dir_ptr = static_cast<double*>(dir_buf.ptr);

        int n_incs = inc_buf.shape[0];
        blueprint.binclusion.reserve(n_incs);
        for (int i = 0; i < n_incs; ++i) {
            int vid = inc_ptr[i*2+1];
            if (vid >= n_verts || vid < 0)
                throw std::runtime_error("Inclusion references invalid vertex index");

            double x = dir_ptr[i*2], y = dir_ptr[i*2+1];
            double norm = sqrt(x*x + y*y);
            if (norm <= 1e-8) { x = 1.0; y = 0.0; } else { x /= norm; y /= norm; }

            Inclusion_Map inc = {x, y, i, vid, inc_ptr[i*2]};
            blueprint.binclusion.push_back(inc);
        }
    }

    blueprint.number_vector_field = 0;
    return blueprint;
};

class CurvatureCalculator : public CurvatureByShapeOperatorType1 {
private:
    MESH* m_pMesh;
    Vec3D *m_pBox;

public:
    CurvatureCalculator(MESH* mesh)
        : CurvatureByShapeOperatorType1(nullptr)
        , m_pMesh(mesh)
    {
        m_pBox = m_pMesh->GetBox();
    }

    bool Initialize() override {
        m_pBox = m_pMesh->GetBox();

        const std::vector<triangle*>& triangles = m_pMesh->GetActiveT();
        for (auto* tri : triangles) {
            tri->UpdateNormal_Area(m_pBox);
        }

        const std::vector<links*>& right_edges = m_pMesh->GetRightL();
        for (auto* link : right_edges) {
            link->UpdateShapeOperator(m_pBox);
        }

        const std::vector<links*>& edge_links = m_pMesh->GetEdgeL();
        for (auto* link : edge_links) {
            link->UpdateEdgeVector(m_pBox);
        }

        const std::vector<vertex*>& surface_vertices = m_pMesh->GetSurfV();
        for (auto* vertex : surface_vertices) {
            UpdateSurfVertexCurvature(vertex);
        }

        const std::vector<vertex*>& edge_vertices = m_pMesh->GetEdgeV();
        for (auto* vertex : edge_vertices) {
            UpdateEdgeVertexCurvature(vertex);
        }

        return true;
    }

private:
    // This just replaces state logging
    Vec3D Calculate_Vertex_Normal(vertex* pvertex, double& area) {
        area = 0.0;
        Vec3D Normal;

        const std::vector<triangle*>& triangles = pvertex->GetVTraingleList();
        for (auto* tri : triangles) {
            const Vec3D& Nv = tri->GetAreaVector();
            Normal = Normal + Nv;
            area += tri->GetArea();
        }

        area /= 3.0;
        if (area < 1e-8) {
            std::cerr << "Error: vertex with id " << pvertex->GetVID()
                      << " has negative or zero area" << std::endl;
            return Normal;
        }

        double normalsize = Normal.norm();
        if (normalsize < 1e-8) {
            std::cerr << "Error: vertex with id " << pvertex->GetVID()
                      << " has zero normal" << std::endl;
            return Normal;
        }

        Normal = Normal * (1.0 / normalsize);
        return Normal;
    }
};



class PyMesh {
private:
    std::unique_ptr<MESH> m_pMesh;
    std::unique_ptr<CurvatureCalculator> m_pCurvature;

    // FreeDTS defines inclusion types after defining meshes. Hence
    // m_InclusionType points to invalid memory at this point. To have
    // access to inclusion type we store the blueprint map
    std::vector<Inclusion_Map> m_Inclusions;

    template<typename T>
    T* get_array_ptr(py::array_t<T>& array) {
        auto buf = array.request();
        return static_cast<T*>(buf.ptr);
    }

    void InitializeFromBlueprint(const MeshBluePrint& blueprint) {
        m_Inclusions = blueprint.binclusion;
        if (!m_pMesh->GenerateMesh(blueprint)) {
            throw std::runtime_error("Failed to generate mesh");
        }

        // This will update all vertex attributes. For now we can compute it once
        // but might need to update the internal parameters if we allow modifying
        // vertices and triangles
        m_pCurvature.reset(new CurvatureCalculator(m_pMesh.get()));
        m_pCurvature->Initialize();
    }

public:
    // File-based constructor
    PyMesh(const std::string& filename) : m_pMesh(new MESH()) {
        CreateMashBluePrint creator;
        MeshBluePrint blueprint = creator.MashBluePrintFromInput_Top("", filename);
        InitializeFromBlueprint(blueprint);
    }

    // Array-based constructor
    PyMesh(py::array_t<double> vertices,
           py::array_t<int> triangles,
           py::array_t<int> inclusions = py::array_t<int>(),
           py::array_t<double> inclusion_directions = py::array_t<double>(),
           py::array_t<double> box_size = py::array_t<double>(),
           py::array_t<int> vertex_domains = py::array_t<int>())
        : m_pMesh(new MESH())
    {
        MeshBluePrint blueprint = CreateBlueprintFromArrays(
            vertices, triangles, inclusions, inclusion_directions, box_size, vertex_domains
        );
        InitializeFromBlueprint(blueprint);
    }

    py::array_t<double> get_vertex_curvatures() {
        const std::vector<vertex*>& vertices = m_pMesh->GetActiveV();
        int n_vertices = static_cast<int>(vertices.size());

        auto result = py::array_t<double>({n_vertices, 2});
        double* ptr = get_array_ptr(result);
        for (int i = 0; i < n_vertices; ++i) {
            vertex* v = vertices[i];
            ptr[i * 2 + 0] = v->GetP1Curvature();
            ptr[i * 2 + 1] = v->GetP2Curvature();
        }
        return result;
    }

    py::array_t<double> get_vertex_normals() {
        const std::vector<vertex*>& vertices = m_pMesh->GetActiveV();
        int n_vertices = static_cast<int>(vertices.size());

        auto result = py::array_t<double>({n_vertices, 3});
        double* ptr = get_array_ptr(result);
        for (int i = 0; i < n_vertices; ++i) {
            const Vec3D& normal = vertices[i]->GetNormalVector();
            ptr[i * 3 + 0] = normal(0);
            ptr[i * 3 + 1] = normal(1);
            ptr[i * 3 + 2] = normal(2);
        }
        return result;
    }

    py::array_t<double> get_vertex_areas() {
        const std::vector<vertex*>& vertices = m_pMesh->GetActiveV();
        int n_vertices = static_cast<int>(vertices.size());

        auto result = py::array_t<double>({n_vertices});
        double* ptr = get_array_ptr(result);
        for (int i = 0; i < n_vertices; ++i) {
            ptr[i] = vertices[i]->GetArea();
        }
        return result;
    }

    py::array_t<double> get_vertex_positions() {
        const std::vector<vertex*>& vertices = m_pMesh->GetActiveV();
        int n_vertices = static_cast<int>(vertices.size());

        auto result = py::array_t<double>({n_vertices, 3});
        double* ptr = get_array_ptr(result);
        for (int i = 0; i < n_vertices; ++i) {
            vertex* v = vertices[i];
            ptr[i * 3 + 0] = v->GetVXPos();
            ptr[i * 3 + 1] = v->GetVYPos();
            ptr[i * 3 + 2] = v->GetVZPos();
        }
        return result;
    }

    py::array_t<int> get_triangles() {
        const std::vector<triangle*>& triangles = m_pMesh->GetActiveT();
        int n_triangles = static_cast<int>(triangles.size());

        auto result = py::array_t<int>({n_triangles, 3});
        int* ptr = get_array_ptr(result);
        for (int i = 0; i < n_triangles; ++i) {
            triangle* t = triangles[i];
            ptr[i * 3 + 0] = t->GetV1()->GetVID();
            ptr[i * 3 + 1] = t->GetV2()->GetVID();
            ptr[i * 3 + 2] = t->GetV3()->GetVID();
        }
        return result;
    }

    std::pair<py::array_t<int>, py::array_t<int>> get_vertex_inclusion_mapping() {
        int n_inclusions = static_cast<int>(m_Inclusions.size());
        auto vertex_ids = py::array_t<int>({n_inclusions});
        auto inclusion_type_ids = py::array_t<int>({n_inclusions});

        if (n_inclusions > 0) {
            int* vertex_ptr = static_cast<int*>(vertex_ids.request().ptr);
            int* inclusion_ptr = static_cast<int*>(inclusion_type_ids.request().ptr);

            for (int i = 0; i < n_inclusions; ++i) {
                vertex_ptr[i] = m_Inclusions[i].vid;
                inclusion_ptr[i] = m_Inclusions[i].tid;
            }
        }
        return std::make_pair(vertex_ids, inclusion_type_ids);
    }
};

PYBIND11_MODULE(_core, m) {
    py::class_<PyMesh>(m, "Mesh")
        .def(py::init<const std::string&>(), py::arg("filename"),
             "Load mesh from file and initialize curvature calculator.")
        .def(py::init<py::array_t<double>, py::array_t<int>, py::array_t<int>,
                      py::array_t<double>, py::array_t<double>, py::array_t<int>>(),
             py::arg("vertices"), py::arg("triangles"),
             py::arg("inclusions") = py::array_t<int>(),
             py::arg("inclusion_directions") = py::array_t<double>(),
             py::arg("box_size") = py::array_t<double>(),
             py::arg("vertex_domains") = py::array_t<int>(),
             "Create mesh from vertex positions, triangle connectivity, and optional inclusions.")
        .def_property("vertices", &PyMesh::get_vertex_positions, nullptr,
             "Get vertex positions as numpy array (N, 3)")
        .def_property("triangles", &PyMesh::get_triangles, nullptr,
             "Get triangle connectivity as numpy array (M, 3)")
        .def("get_vertex_curvatures", &PyMesh::get_vertex_curvatures,
             "Get principal curvature 1 and 2 for all vertices (N, 2)")
        .def("get_vertex_normals", &PyMesh::get_vertex_normals,
             "Get vertex normals (N, 3)")
        .def("get_vertex_areas", &PyMesh::get_vertex_areas,
             "Get vertex area (N,)")
        .def("get_vertex_inclusion_mapping", &PyMesh::get_vertex_inclusion_mapping,
             "Get mapping of vertex IDs to inclusion type IDs");
}