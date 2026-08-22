"""Tests del parseo de argumentos de línea de comandos en main.py."""

from main import SEED, _resolve_seed


def test_without_random_flag_uses_fixed_seed():
    assert _resolve_seed([]) == SEED


def test_with_random_flag_uses_randint_fn():
    seed = _resolve_seed(["main.py", "--random"], randint_fn=lambda a, b: 12345)
    assert seed == 12345


def test_with_random_flag_calls_randint_fn_with_a_range():
    seen = {}

    def fake_randint(a, b):
        seen["range"] = (a, b)
        return 0

    _resolve_seed(["--random"], randint_fn=fake_randint)

    a, b = seen["range"]
    assert a < b
