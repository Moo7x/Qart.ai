"""Real-data job signal from public ATS job boards (Greenhouse, Lever, Ashby).

These boards list only CURRENTLY open jobs, so history is built by saving a dated snapshot each
run and tracking when each job first and last appeared (first_seen / last_seen).
"""
