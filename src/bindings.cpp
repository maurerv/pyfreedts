#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <memory>

#include "pyfreedts/_cpp/dts_src/MESH.h"
#include "pyfreedts/_cpp/dts_src/CreateMashBluePrint.h"
#include "pyfreedts/_cpp/dts_src/CurvatureByShapeOperatorType1.h"

namespace py = pybind11;

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

public:
    PyMesh(const std::string& filename)
        : m_pMesh(new MESH())
    {
        CreateMashBluePrint creator;
        MeshBluePrint blueprint = creator.MashBluePrintFromInput_Top("", filename);

        m_Inclusions = blueprint.binclusion;
        if (!m_pMesh->GenerateMesh(blueprint)) {
            throw std::runtime_error("Failed to generate mesh from file: " + filename);
        }

        m_pCurvature.reset(new CurvatureCalculator(m_pMesh.get()));

        // This will update all vertex attributes. For now we can compute it once
        // but might need to update the internal parameters if we allow modifying
        // vertices and triangles
        m_pCurvature->Initialize();
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
            vertex* v = vertices[i];
            const Vec3D& normal = v->GetNormalVector();
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
            vertex* v = vertices[i];
            ptr[i] = v->GetArea();
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
            auto vertex_buf = vertex_ids.request();
            auto inclusion_buf = inclusion_type_ids.request();

            int* vertex_ptr = static_cast<int*>(vertex_buf.ptr);
            int* inclusion_ptr = static_cast<int*>(inclusion_buf.ptr);

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
        .def_property("vertices", &PyMesh::get_vertex_positions, nullptr,
             "Get vertex positions as numpy array (N, 3),")
        .def_property("triangles", &PyMesh::get_triangles, nullptr,
             "Get triangle connectivity as numpy array (M, 3),")
        .def("get_vertex_curvatures", &PyMesh::get_vertex_curvatures,
             "Get principal curvatuer 1 and 2 for all vertices (N, 2),")
        .def("get_vertex_normals", &PyMesh::get_vertex_normals,
             "Get vertex normals (N, 3),")
        .def("get_vertex_areas", &PyMesh::get_vertex_areas,
             "Get vertex area (N,).")
        .def("get_vertex_inclusion_mapping", &PyMesh::get_vertex_inclusion_mapping,
             "Get mapping of vertex IDs to inclusion type IDs");
}