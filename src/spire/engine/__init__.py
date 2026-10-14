"""Original-game plumbing shared by every track: Windows runtime, relay bridge, doctor.

``windows_relay.py`` runs under Windows Python and imports nothing from this package.
``runtime`` deploys it, with the supervisor ``gameai/windows_game.py``, to
``C:/spire-agent``.
"""
