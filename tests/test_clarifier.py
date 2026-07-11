import unittest

from pyquda_agent.tasks.clarifier import apply_answer
from pyquda_agent.tasks.clarifier import build_questions
from pyquda_agent.tasks.clarifier import determine_missing_fields
from pyquda_agent.tasks.schema import Pion2ptTaskDraft


class ClarifierTests(unittest.TestCase):
    def test_missing_fields_and_answers(self):
        draft = Pion2ptTaskDraft(
            task_type="pion_2pt",
            workflow_id="pion_2pt_chroma_wall_local_zero_momentum_npy_v1",
        )
        missing = determine_missing_fields(draft)
        self.assertIn("start_from", missing)
        self.assertIn("has_existing_propagators", missing)
        self.assertIn("cluster_launch", missing)
        questions = build_questions(draft, max_questions=3)
        self.assertEqual(questions[0].field_name, "start_from")
        self.assertEqual(questions[1].field_name, "has_existing_propagators")

        apply_answer(draft, "start_from", "gauge")
        apply_answer(draft, "has_existing_propagators", "no")
        apply_answer(draft, "gauge_format", "chroma_qio")
        apply_answer(draft, "gauge_path", "/tmp/cfg_0001.lime")
        apply_answer(draft, "lattice_size", "24 24 24 72")
        apply_answer(draft, "grid_size", "1 1 1 2")
        apply_answer(draft, "fermion_action", "clover")
        apply_answer(draft, "mass", "0.09253")
        apply_answer(draft, "xi_0", "4.8965")
        apply_answer(draft, "nu", "0.86679")
        apply_answer(draft, "coeff_t", "0.8549165664")
        apply_answer(draft, "coeff_r", "2.32582045")
        apply_answer(draft, "solver_tol", "1e-12")
        apply_answer(draft, "solver_maxiter", "1000")
        apply_answer(draft, "source_type", "wall")
        apply_answer(draft, "sink_type", "local")
        apply_answer(draft, "momentum_projection", "zero")
        apply_answer(draft, "source_timeslices", "0")
        apply_answer(draft, "gauge_fixed", "no")
        apply_answer(draft, "correlator_output_format", "npy")
        apply_answer(draft, "correlator_output_path", "outputs/pion.npy")
        apply_answer(draft, "resource_path", ".cache/quda")
        apply_answer(draft, "cluster_launch", "local")
        apply_answer(draft, "script_output_path", "outputs/run_pion.py")
        apply_answer(draft, "script_style", "complete")

        self.assertEqual(determine_missing_fields(draft), [])
        self.assertEqual(draft.momenta, [[0, 0, 0]])
        self.assertFalse(draft.gauge_fixed)
        self.assertEqual(draft.correlator_output_format, "npy")
        self.assertEqual(draft.cluster_launch, "local")


if __name__ == "__main__":
    unittest.main()
