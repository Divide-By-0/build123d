"""Production regression for STEP relabelling of spindle-torus faces.

The native BREP fixture is the reference solid matched as reference index 2
to candidate index 0 in Quests Assembly Verifier sample
``esmp_7e4d5169ac2e4b43a5`` from run ``erun_3f8c8d08555b49cd9c``
(the Connector Assembly challenge).  It is stored as BREP so the STEP write
under test does not bake the faulty surface conversion into the fixture.

In production, a build123d import/export round trip preserved the solid's
volume and exact B-Rep to about 5e-10 relative error, but changed four
``Geom_ToroidalSurface`` faces into ``Geom_SurfaceOfRevolution``.  The
Assembly Verifier consequently measured a 1.476% face-signature disagreement
and assigned this geometrically unchanged solid a normalized shape distance
of 14.76.
"""

from pathlib import Path

import pytest

from OCP.BRepAdaptor import BRepAdaptor_Surface

from build123d import GeomType, import_brep, import_step
from build123d.exporters3d import export_step

ASSETS = Path(__file__).parent / "assets"
FIXTURE = ASSETS / "connector_retention_clip_spindle_tori.brep"


def _faces_of_type(shape, geometry_type: GeomType):
    return [face for face in shape.faces() if face.geom_type == geometry_type]


class TestConnectorSpindleTorusFidelity:
    """A STEP round trip must not relabel valid spindle-torus faces."""

    def test_the_production_asset_is_pristine(self):
        clip = import_brep(FIXTURE)

        assert len(clip.faces()) == 76
        assert clip.volume == pytest.approx(2.690482, abs=1e-6)
        assert len(_faces_of_type(clip, GeomType.TORUS)) == 12
        assert len(_faces_of_type(clip, GeomType.REVOLUTION)) == 0

        spindle_tori = []
        for face in _faces_of_type(clip, GeomType.TORUS):
            torus = BRepAdaptor_Surface(face.wrapped).Torus()
            if torus.MajorRadius() < torus.MinorRadius():
                spindle_tori.append(torus)

        assert len(spindle_tori) == 4
        for torus in spindle_tori:
            assert torus.MajorRadius() == pytest.approx(0.05, abs=2e-12)
            assert torus.MinorRadius() == pytest.approx(0.20, abs=3e-12)

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "OCCT STEP writer converts four R<r spindle tori to "
            "SURFACE_OF_REVOLUTION, producing a 1.476% face-signature error"
        ),
    )
    def test_spindle_tori_survive_a_step_round_trip(self, tmp_path):
        clip = import_brep(FIXTURE)
        step_path = tmp_path / "connector-retention-clip.step"

        assert export_step(clip, step_path)
        returned = import_step(step_path)

        assert len(returned.faces()) == 76
        assert len(_faces_of_type(returned, GeomType.TORUS)) == 12
        assert len(_faces_of_type(returned, GeomType.REVOLUTION)) == 0
