"""Tests for the Hyperbolic LLM client. All HTTP is mocked."""

import json
import unittest
from unittest.mock import patch

import requests

from dashboard import llm_client
from dashboard.llm_client import FALLBACK_TEXT, LLMResponse, ask


CONTEXT = {"kpi": "ROAS", "items": [], "focus_id": None}


def fake_response(status=200, payload=None):
    class FakeResponse:
        status_code = status

        def json(self):
            if payload is None:
                raise ValueError("no json")
            return payload

    return FakeResponse()


@patch.dict("os.environ", {"HYPERBOLIC_KEY": "test-key"})
class AskTests(unittest.TestCase):
    def test_success_returns_answer_text(self):
        payload = {"choices": [{"message": {"content": " The lift is +42%. "}}]}
        with patch.object(requests, "post", return_value=fake_response(200, payload)):
            result = ask(CONTEXT, [], "what does this mean?")
        self.assertEqual(result, LLMResponse(text="The lift is +42%.", ok=True))

    def test_non_200_falls_back(self):
        with patch.object(requests, "post", return_value=fake_response(429, {})):
            result = ask(CONTEXT, [], "q")
        self.assertFalse(result.ok)
        self.assertEqual(result.text, FALLBACK_TEXT)

    def test_timeout_falls_back(self):
        with patch.object(requests, "post", side_effect=requests.Timeout):
            result = ask(CONTEXT, [], "q")
        self.assertFalse(result.ok)
        self.assertEqual(result.text, FALLBACK_TEXT)

    def test_malformed_body_falls_back(self):
        with patch.object(requests, "post", return_value=fake_response(200, {"choices": []})):
            result = ask(CONTEXT, [], "q")
        self.assertFalse(result.ok)

    def test_empty_answer_falls_back(self):
        payload = {"choices": [{"message": {"content": "   "}}]}
        with patch.object(requests, "post", return_value=fake_response(200, payload)):
            result = ask(CONTEXT, [], "q")
        self.assertFalse(result.ok)

    def test_context_sent_as_user_role_not_system(self):
        payload = {"choices": [{"message": {"content": "ok"}}]}
        with patch.object(requests, "post", return_value=fake_response(200, payload)) as post:
            ask(CONTEXT, [], "q")
        messages = post.call_args.kwargs["json"]["messages"]
        system_messages = [m for m in messages if m["role"] == "system"]
        context_json = json.dumps(CONTEXT, default=str)
        self.assertEqual(len(system_messages), 1)
        self.assertNotIn(context_json, system_messages[0]["content"])
        self.assertIn(context_json, messages[1]["content"])
        self.assertEqual(messages[1]["role"], "user")

    def test_history_is_trimmed_and_question_is_last(self):
        payload = {"choices": [{"message": {"content": "ok"}}]}
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"}
            for i in range(40)
        ]
        with patch.object(requests, "post", return_value=fake_response(200, payload)) as post:
            ask(CONTEXT, history, "final question")
        messages = post.call_args.kwargs["json"]["messages"]
        sent_history = [m for m in messages if m["content"].startswith("m")]
        self.assertEqual(len(sent_history), llm_client.MAX_HISTORY_MESSAGES)
        self.assertEqual(sent_history[-1]["content"], "m39")
        self.assertEqual(messages[-1], {"role": "user", "content": "final question"})

    def test_timeout_is_set_on_request(self):
        payload = {"choices": [{"message": {"content": "ok"}}]}
        with patch.object(requests, "post", return_value=fake_response(200, payload)) as post:
            ask(CONTEXT, [], "q")
        self.assertEqual(post.call_args.kwargs["timeout"], llm_client.TIMEOUT_SECONDS)


class MissingKeyTests(unittest.TestCase):
    def test_missing_key_falls_back_without_http(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(requests, "post") as post:
                result = ask(CONTEXT, [], "q")
        post.assert_not_called()
        self.assertFalse(result.ok)
        self.assertEqual(result.text, FALLBACK_TEXT)


if __name__ == "__main__":
    unittest.main()
