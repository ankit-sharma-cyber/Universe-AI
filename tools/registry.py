from tools.base import BaseTool
from tools.calendar import CalendarTool
from tools.email import EmailTool
from tools.notification import NotificationTool
from tools.registration import RegistrationTool

TOOLS: dict[str, BaseTool] = {
    tool.name: tool for tool in [CalendarTool(), EmailTool(), RegistrationTool(), NotificationTool()]
}


def get_tool(name: str) -> BaseTool:
    return TOOLS[name]


def tool_schemas() -> list[dict]:
    return [{"name": t.name, "description": t.description} for t in TOOLS.values()]
