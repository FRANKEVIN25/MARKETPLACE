"""Pure helpers shared by the load generator and result validation."""

import hashlib
import json

VERSION = 3


def company_plan(users):
    """Largest-remainder allocation for A:B:C = 1:2:3, without random drift."""
    if users < 1:
        raise ValueError('At least one user is required')
    counts = [users * weight // 6 for weight in (1, 2, 3)]
    remaining = users - sum(counts)
    order = sorted(range(3), key=lambda i: (-(users * (i + 1) % 6), i))
    for index in order[:remaining]:
        counts[index] += 1
    # Interleave companies while preserving the exact integer allocation.
    result = []
    while any(counts):
        for index, letter in enumerate('ABC'):
            if counts[index]:
                result.append(letter)
                counts[index] -= 1
    return result


def fingerprint(configuration, policy):
    payload = json.dumps({'configuration': configuration, 'policy': policy},
                         sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def comparison_policy(metadata):
    return {key: metadata[key] for key in (
        'protocol_version', 'mode', 'purpose', 'spawn_rate', 'warmup_seconds',
        'duration_seconds', 'seed', 'company_weights', 'read_mix',
        'locust_script_sha256', 'protocol_script_sha256', 'runner_script_sha256',
        'experiment_id', 'request_connection',
    )}
