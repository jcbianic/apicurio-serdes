"""Conftest for 004-kafka-headers-wire-format step definitions.

Registers the feature file base directory so @scenario decorators
can use paths relative to specs/004-kafka-headers-wire-format/tests/features/.
"""

from __future__ import annotations

# Feature file base path for 004-kafka-headers-wire-format BDD scenarios.
# Step definition files in this directory reference .feature files via
# @scenario with paths relative to this base.
FEATURES_BASE = "../../specs/004-kafka-headers-wire-format/tests/features"
