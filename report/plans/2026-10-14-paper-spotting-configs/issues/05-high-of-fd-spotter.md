# 05 — OF-FD / fixed-ROI optical-flow feature-difference spotter

**Severity:** high

**Status:** done as proxy — `of_fd_proxy` uses cached POC-ABS ROI motion curves with OF-FD-style denoising/peak/NMS. It improves interval cleanliness/precision options but does not beat baseline loose F1, so true dense OF remains a separate heavier next step.

## Current Problem

MDMD is known to be brutally weak under MEGC2020 long-video scoring. A more
informative training-free comparator is the modern optical-flow feature-difference
family: face/nose alignment, fixed facial ROIs, dense optical-flow time curves,
peak detection, and NMS/boundary refinement.

## Target

Implement a credible OF-FD candidate in the repo's style:

- if possible, compute true dense optical flow on aligned/cropped ROI frames
  using OpenCV; otherwise start from POC-ABS ROI signal approximation and label it
  `of_fd_proxy`
- use fixed facial ROI groups comparable to the paper family (14 ROI target;
  adapt from available dlib/ROI definitions if exact masks are unavailable)
- aggregate ROI flow/time curves with top-ROI or precision-oriented selection
- denoise with existing Savitzky-Golay / low-pass options first; add EMD only if
  dependency cost is justified
- peak detection + NMS using common evaluator

Source mapping:
- MM'21 “Research on Micro-Expression Spotting Method Based on Optical Flow
  Features”: nose-tip/crop alignment, optical flow from 14 ROIs, wave peak
  localization; reported as significantly better than baseline on CAS(ME)²-cropped
  and SAMM-LV.
- Later OF/MSOF/OFCT family: 13/14 ROIs, main/secondary direction optical flow,
  low-pass/EMD, threshold screening, NMS.

## Required Design

- This is the main training-free comparator, not MDMD.
- Report precision-oriented metrics because false positives poison anxiety
  recognition features.
- Do not introduce heavy new dependencies without evidence the lighter version is
  insufficient.

## Tests

Allowed syntax/limit evaluator runs only unless Khalid asks for full run.

## Done Criteria

- [x] OF-FD or OF-FD-proxy appears in evaluator results.
- [x] Summary states whether POC-ABS loses to optical-flow FD; if yes, motion
      estimation is the weak link and production should move that way.
