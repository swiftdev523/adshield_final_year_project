"""Backend package for the Android Adware Detection and Prevention System.

Sub-packages:
    apk_analysis   APK Analysis Mode: parse an APK, extract permissions, and
                   convert them into the model's training feature format.

This package intentionally does NOT load or run the ML model. It only prepares
features so that a later scoring layer can consume them.
"""
