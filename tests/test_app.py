from pathlib import Path
import unittest

from fastapi.testclient import TestClient
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.tools.function_tool import FunctionTool

from personal_assistant.agent import root_agent
from personal_assistant.tools import analyze_text, calculate


class AppTests(unittest.TestCase):
    def test_three_tools_and_function_schemas(self):
        self.assertEqual(len(root_agent.tools), 3)
        self.assertEqual(root_agent.sub_agents, [])
        self.assertEqual(root_agent.tools[0].name, "google_search")
        self.assertTrue(root_agent.tools[0].bypass_multi_tools_limit)
        for function, argument in ((calculate, "expression"), (analyze_text, "text")):
            declaration = FunctionTool(func=function)._get_declaration()
            properties = (declaration.parameters_json_schema["properties"]
                          if declaration.parameters_json_schema
                          else declaration.parameters.properties)
            self.assertIn(argument, properties)

    def test_web_ui_and_agent_discovery(self):
        agents = Path(__file__).resolve().parents[1] / "agents"
        app = get_fast_api_app(agents_dir=str(agents), web=True, use_local_storage=False)
        with TestClient(app) as client:
            response = client.get("/list-apps")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(set(response.json()), {"personal_assistant", "smart_study"})
            page = client.get("/dev-ui/")
            self.assertEqual(page.status_code, 200)
            self.assertIn("html", page.headers["content-type"])


if __name__ == "__main__":
    unittest.main()
