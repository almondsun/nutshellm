from nutshellm.config import Settings


def test_production_readiness_requires_pricing_and_secret_controls():
    errors = Settings(
        environment="production",
        paritok_api_key="configured",
        task_model_api_key="configured",
        turnstile_secret_key="configured",
        session_signing_secret="configured",
    ).validate_production()
    assert any("INPUT_USD" in error for error in errors)
    assert any("OUTPUT_USD" in error for error in errors)


def test_budget_reservation_is_positive_when_prices_are_configured():
    settings = Settings(
        task_input_usd_per_mtok=1,
        task_output_usd_per_mtok=2,
    )
    assert settings.run_budget_reservation_usd() > 0
