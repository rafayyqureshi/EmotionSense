"""Contract tests use Flask's real test client; provider responses are mocked."""
import io
import math
import unittest
from unittest.mock import Mock, patch

import app as web
from emotion_core import classifier_analysis, keyword_analysis, normalize_scores


class ScoreTests(unittest.TestCase):
    def test_fallback_is_repeatable(self):
        first = keyword_analysis("I am happy but worried!")
        for _ in range(20):
            self.assertEqual(first, keyword_analysis("I am happy but worried!"))

    def test_whole_words_do_not_misread_unhappy_as_happy(self):
        result = keyword_analysis("I am unhappy")
        self.assertEqual(result.scores["happy"], 0)
        self.assertEqual(result.scores["sad"], 1)

    def test_rule_matching_is_case_insensitive(self):
        self.assertEqual(keyword_analysis("JOY"), keyword_analysis("joy"))

    def test_no_signal_uses_an_explicit_neutral_rule(self):
        result = keyword_analysis("The parcel contains a document.")
        self.assertEqual(result.scores["neutral"], 1)
        self.assertTrue(result.used_fallback)

    def test_scores_are_finite_and_normalized(self):
        result = keyword_analysis("happy sad worried surprised")
        self.assertAlmostEqual(sum(result.scores.values()), 1)
        self.assertTrue(all(math.isfinite(x) and x >= 0 for x in result.scores.values()))

    def test_invalid_scores_are_rejected(self):
        for value in (-1, float("nan"), float("inf"), True, "0.5"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_scores({"happy": value})

    def test_zero_scores_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_scores({"happy": 0})

    def test_flat_and_batched_provider_shapes_are_supported(self):
        rows = [{"label": "joy", "score": 0.8}, {"label": "sadness", "score": 0.2}]
        self.assertEqual(classifier_analysis(rows), classifier_analysis([rows]))

    def test_unknown_classifier_labels_do_not_become_fake_neutral_predictions(self):
        with self.assertRaises(ValueError):
            classifier_analysis([{"label": "LABEL_0", "score": 1}])


class ApiTests(unittest.TestCase):
    def setUp(self):
        web.app.config.update(TESTING=True)
        self.client = web.app.test_client()
        self.key_patch = patch.object(web, "API_KEY", "")
        self.key_patch.start()
        self.addCleanup(self.key_patch.stop)

    def post_comment(self, comment="I am happy", model="bert"):
        return self.client.post("/api/analyze", json={"comment": comment, "model_type": model})

    def upload(self, content, filename="comments.csv", model="bert"):
        return self.client.post("/api/batch", data={
            "file": (io.BytesIO(content.encode("utf-8")), filename),
            "model_type": model,
        }, content_type="multipart/form-data")

    def test_home_page_renders(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_missing_credentials_never_send_a_provider_request(self):
        with patch.object(web.requests, "post") as remote:
            response = self.post_comment()
        remote.assert_not_called()
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["provenance"]["method"], "local_keywords")
        self.assertFalse(data["provenance"]["is_model_prediction"])

    def test_successful_remote_classifier_is_labeled(self):
        payload = [{"label": "joy", "score": 0.9}, {"label": "sadness", "score": 0.1}]
        with patch.object(web, "query_huggingface_api", return_value=payload):
            data = self.post_comment().get_json()
        self.assertEqual(data["provenance"]["method"], "remote_classifier")
        self.assertTrue(data["provenance"]["is_model_prediction"])
        self.assertFalse(data["provenance"]["used_fallback"])

    def test_malformed_provider_result_becomes_labeled_fallback(self):
        with patch.object(web, "query_huggingface_api", return_value={"error": "not ready"}):
            data = self.post_comment().get_json()
        self.assertEqual(data["provenance"]["method"], "local_keywords")
        self.assertTrue(data["provenance"]["used_fallback"])

    def test_provider_timeout_is_bounded_and_falls_back(self):
        with patch.object(web, "API_KEY", "test-only"), patch.object(
            web.requests, "post", side_effect=web.requests.Timeout
        ) as remote:
            response = self.post_comment()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(remote.call_args.kwargs["timeout"], web.API_TIMEOUT)
        self.assertTrue(response.get_json()["provenance"]["used_fallback"])

    def test_provider_http_error_falls_back(self):
        remote_response = Mock(status_code=503)
        with patch.object(web, "API_KEY", "test-only"), patch.object(
            web.requests, "post", return_value=remote_response
        ) as remote:
            response = self.post_comment()
        self.assertEqual(remote.call_count, 1)
        self.assertTrue(response.get_json()["provenance"]["used_fallback"])

    def test_generated_text_scores_are_not_claimed_as_classifier_predictions(self):
        with patch.object(web, "query_huggingface_api", return_value=[{"generated_text": "joy"}]):
            data = self.post_comment(model="gpt").get_json()
        self.assertEqual(data["provenance"]["method"], "generated_text_keywords")
        self.assertFalse(data["provenance"]["is_model_prediction"])

    def test_ensemble_reports_its_component_sources(self):
        data = self.post_comment(model="ensemble").get_json()
        self.assertEqual(data["provenance"]["components"], ["local_keywords", "local_keywords"])
        self.assertTrue(data["provenance"]["used_fallback"])
        self.assertAlmostEqual(sum(data["emotions"].values()), 1)

    def test_non_object_json_and_bad_comment_types_are_client_errors(self):
        payloads = [[], None, 3, {"comment": []}, {"comment": True}, {"comment": "  "}]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.post("/api/analyze", json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())

    def test_malformed_json_is_a_client_error(self):
        response = self.client.post("/api/analyze", data="{", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_unknown_pipeline_is_rejected(self):
        self.assertEqual(self.post_comment(model="unknown").status_code, 400)

    def test_oversized_comment_is_rejected(self):
        self.assertEqual(self.post_comment(comment="x" * 5001).status_code, 400)

    def test_csv_requires_the_comment_column(self):
        self.assertEqual(self.upload("text\nhello\n").status_code, 400)

    def test_csv_skips_blank_cells_instead_of_classifying_nan(self):
        data = self.upload('comment,other\n,1\n"happy",2\n,3\n').get_json()
        self.assertEqual(data["processed_count"], 1)
        self.assertEqual(data["results"][0]["comment"], "happy")

    def test_csv_processes_each_selected_comment_once(self):
        payload = [{"label": "joy", "score": 1}]
        with patch.object(web, "query_huggingface_api", return_value=payload) as remote:
            data = self.upload("comment\nhappy\nsad\n").get_json()
        self.assertEqual(data["processed_count"], 2)
        self.assertEqual(remote.call_count, 2)

    def test_csv_row_limit_is_visible(self):
        data = self.upload("comment\n" + "\n".join(["happy"] * 7)).get_json()
        self.assertEqual(data["processed_count"], 5)
        self.assertEqual(data["total_rows"], 7)
        self.assertTrue(data["truncated"])
        self.assertIn("warning", data)

    def test_csv_invalid_model_and_file_type_are_rejected(self):
        self.assertEqual(self.upload("comment\nhappy\n", model="unknown").status_code, 400)
        self.assertEqual(self.upload("comment\nhappy\n", filename="comments.txt").status_code, 400)

    def test_missing_upload_is_a_client_error(self):
        self.assertEqual(self.client.post("/api/batch").status_code, 400)

    def test_csv_parse_error_is_a_client_error(self):
        self.assertEqual(self.upload('comment\n"unterminated').status_code, 400)

    def test_empty_csv_is_a_client_error(self):
        self.assertEqual(self.upload("").status_code, 400)

    def test_large_upload_returns_json_413(self):
        with patch.dict(web.app.config, {"MAX_CONTENT_LENGTH": 100}):
            response = self.upload("comment\n" + "x" * 200)
        self.assertEqual(response.status_code, 413)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()
