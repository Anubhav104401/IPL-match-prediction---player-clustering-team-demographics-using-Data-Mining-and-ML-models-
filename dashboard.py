"""
Backwards-compatible entry point.

The dashboard was rebuilt as a multi-page application; ``app.py`` is now the
canonical entry point. This shim is kept so the command documented throughout
the project and printed by ``main.py`` keeps working:

    streamlit run dashboard.py

It is equivalent to:

    streamlit run app.py
"""

from app import main

main()
