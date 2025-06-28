from rich.panel import Panel

from rich.console import RenderableType
from rich import print as rprint


def log_title(renderable: RenderableType = "", title: str = "-"):
    # 输出panel对象
    rprint(
        Panel(
            renderable,
            title=title,
        )
    )