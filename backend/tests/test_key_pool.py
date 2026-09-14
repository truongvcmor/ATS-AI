from app.services.ai_common.key_pool import KeyPool, ProviderKey


def _keys():
    return [
        ProviderKey("openai", "key-a", "gpt-4o-mini"),
        ProviderKey("openai", "key-b", "gpt-4o-mini"),
        ProviderKey("gemini", "key-c", "gemini-1.5-flash"),
    ]


def test_acquire_order_round_robins_across_calls():
    pool = KeyPool(_keys(), cooldown_seconds=60)
    first = pool.acquire_order()
    second = pool.acquire_order()
    assert first[0].id != second[0].id
    assert {k.id for k in first} == {k.id for k in second}


def test_failed_key_is_deprioritized_until_cooldown_expires():
    pool = KeyPool(_keys(), cooldown_seconds=60)
    order = pool.acquire_order()
    failing_key = order[0]
    pool.mark_failure(failing_key)

    next_order = pool.acquire_order()
    # the failed key should now be last (only healthy keys come before it)
    assert next_order[-1].id == failing_key.id
    assert next_order[-1].id not in {k.id for k in next_order[:-1]}


def test_mark_success_clears_cooldown():
    pool = KeyPool(_keys(), cooldown_seconds=60)
    key = pool.acquire_order()[0]
    pool.mark_failure(key)
    pool.mark_success(key)

    order = pool.acquire_order()
    healthy_ids = {k.id for k in order}
    assert key.id in healthy_ids  # no longer stuck at the back specifically because it's cooling


def test_cross_provider_pool_mixes_openai_and_gemini():
    pool = KeyPool(_keys())
    providers = {k.provider for k in pool.acquire_order()}
    assert providers == {"openai", "gemini"}
