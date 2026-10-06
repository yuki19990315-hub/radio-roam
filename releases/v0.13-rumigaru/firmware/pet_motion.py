"""Attack displacement in the 120x120 logical viewport."""
PHASE_MS = 650


def leap(elapsed):
    elapsed = max(0, min(PHASE_MS, elapsed))
    # Crouch, leap toward the opponent, brief contact, then return home.
    if elapsed < 80:
        return -2 * elapsed // 80, 1
    if elapsed < 270:
        t = elapsed - 80
        return -2 + 22*t//190, -(8*4*t*(190-t)//(190*190))
    if elapsed < 350:
        return 20, 0
    if elapsed < 610:
        t = elapsed-350
        return 20-20*t//260, -(3*4*t*(260-t)//(260*260))
    return 0, 0
