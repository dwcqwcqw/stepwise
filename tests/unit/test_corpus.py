"""Prevent the retired source or a stale deployment bundle re-entering RAG."""
import pytest
from shared.corpus import SOURCE_IDS, validate_points, validate_sources

def approved_points():
    return [{'payload': {'source_id': source, 'kind': 'band_descriptor'}}
            for source, count in [('ielts-writing-band-descriptors-2023',333),
                                  ('ielts-key-assessment-criteria',26)]
            for _ in range(count)]

def test_two_source_bundle_is_accepted():
    validate_sources([{'id':source} for source in SOURCE_IDS])
    validate_points(approved_points())

def test_third_source_in_lock_is_rejected():
    with pytest.raises(ValueError,match='two approved'):
        validate_sources([{'id':source} for source in [*SOURCE_IDS,'retired-source']])

def test_stale_bundle_is_rejected():
    with pytest.raises(ValueError,match='Rebuild'):
        validate_points(approved_points()+[{'payload':{'source_id':'retired-source','kind':'teaching_guidance'}}])

def test_contamination_cannot_hide_behind_correct_point_count():
    points=approved_points();points[0]['payload']['source_id']='retired-source'
    with pytest.raises(ValueError,match='Rebuild'): validate_points(points)

def test_teaching_records_cannot_masquerade_as_official_criteria():
    points=approved_points();points[0]['payload']['kind']='teaching_guidance'
    with pytest.raises(ValueError,match='Retired'): validate_points(points)
