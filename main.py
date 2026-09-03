import sys
from pathlib import Path

from streamlit.web import cli as streamlit_cli


sys.argv = ["streamlit", "run", str(Path(__file__).with_name("portal.py")), *sys.argv[1:]]
raise SystemExit(streamlit_cli.main())
