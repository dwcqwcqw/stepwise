"""Contract for the two approved official IELTS resources."""
from collections import Counter

SOURCE_IDS = frozenset({
    'ielts-writing-band-descriptors-2023',
    'ielts-key-assessment-criteria',
})
POINT_COUNT = 359

def validate_sources(sources):
    ids = [source['id'] for source in sources]
    if len(ids) != len(SOURCE_IDS) or set(ids) != SOURCE_IDS:
        raise ValueError('Only the two approved official IELTS PDFs may be ingested')

def validate_points(points):
    payloads = [point['payload'] for point in points]
    counts = Counter(payload.get('source_id') for payload in payloads)
    expected = {'ielts-writing-band-descriptors-2023': 333,
                'ielts-key-assessment-criteria': 26}
    if len(points) != POINT_COUNT or counts != expected:
        raise ValueError('Rebuild the index from the two approved official IELTS PDFs')
    if any(payload['kind'] == 'teaching_guidance' for payload in payloads):
        raise ValueError('Retired teaching guidance is not allowed in the active index')
