from .agent import Naver

try:
    from ._version import __version__
except ImportError:
    # Fallback for development installs without setuptools-scm
    __version__ = "0.1.0+dev"

__all__ = ["Naver", "__version__"]
