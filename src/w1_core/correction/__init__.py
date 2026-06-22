"""The two-stage bilingual correction engine — w1's crown jewel.

Stage 1 (bias prompt) is built here and handed to the backend per call; stage 2 is the
deterministic post-correction: mask protected terms -> conservative fuzzy/phonetic OOV
snap -> ordered mode-enabled regex families -> unmask.
"""
