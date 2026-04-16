"""One-off emitter for shared-base batch-185 — technical domain (computer vision: detectors, segmenters, VLMs, classical CV, SfM, NeRF/Gaussian Splatting).

Writes 50 rows to data/v2/shared/batch_185.tmp.jsonl with ids shared-09201..09250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_185.tmp.jsonl"
ID_OFFSET = 9200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Swapped the YOLOv8 detector for YOLOv10 in the edge inference stack; the end-to-end NMS-free head trimmed a full millisecond per frame and kept mAP flat on the COCO eval split.", "decision", "technical", False,
     [("YOLOv8", "framework"), ("YOLOv10", "framework"), ("COCO", "publication"), ("NMS", "algorithm")],
     [("YOLOv10", "YOLOv8", "REPLACES"), ("YOLOv10", "NMS", "REPLACES")],
     "why did the edge detector migrate away from YOLOv8 and what latency win came from the new head",
     "yolov10 yolov8 nms free head edge coco latency detector"),
    # --- 2 architecture ---
    ("The open-vocabulary pipeline layers Grounding DINO for text-prompted boxes into SAM 2 for mask propagation; the tracker stays stable across occlusions that the earlier SAM v1 single-frame path missed.", "architecture", "technical", False,
     [("Grounding DINO", "framework"), ("SAM 2", "framework"), ("SAM v1", "framework")],
     [("SAM 2", "SAM v1", "REPLACES"), ("Grounding DINO", "SAM 2", "COMMUNICATES_WITH")],
     "how does the open-vocabulary tracker stack Grounding DINO with SAM 2 across occluded frames",
     "grounding dino sam 2 mask propagation occlusion open vocabulary"),
    # --- 3 milestone ---
    ("DINOv2 backbone fine-tune landed on the defect-inspection head; linear-probe accuracy on the internal dataset climbed past the ResNet-50 baseline by nine points without touching the classifier.", "milestone", "technical", False,
     [("DINOv2", "framework"), ("ResNet-50", "algorithm"), ("linear-probe", "method")],
     [("DINOv2", "ResNet-50", "IMPROVES_ON")],
     "which self-supervised backbone replaced ResNet-50 on defect inspection and by how much",
     "dinov2 resnet50 linear probe defect inspection backbone"),
    # --- 4 decision ---
    ("Picked RT-DETR over DETR for the production detector; the hybrid encoder and IoU-aware query selection closed the convergence gap that made vanilla DETR need three times the epochs.", "decision", "technical", False,
     [("RT-DETR", "framework"), ("DETR", "framework"), ("IoU-aware query selection", "method")],
     [("RT-DETR", "DETR", "REPLACES"), ("RT-DETR", "IoU-aware query selection", "USES")],
     "which detector won over DETR for production and what feature fixed the convergence complaint",
     "rt detr detr hybrid encoder iou query selection convergence"),
    # --- 5 fact ---
    ("The zero-shot classifier uses EVA-CLIP image-text embeddings; the larger visual transformer gives a consistent four-point top-1 lift over the original CLIP ViT-L/14 on LVIS-style long-tail labels.", "fact", "technical", False,
     [("EVA-CLIP", "framework"), ("CLIP", "framework"), ("ViT-L/14", "algorithm"), ("LVIS", "publication")],
     [("EVA-CLIP", "CLIP", "IMPROVES_ON")],
     "which CLIP variant did the zero-shot head adopt and what kind of labels saw the biggest gain",
     "eva clip vit l 14 long tail lvis zero shot embedding"),
    # --- 6 problem ---
    ("Camera calibration drift on the AR headset came from a thermal-expansion shift in the baseline; the homography recompute at boot stopped compensating correctly once the device warmed past forty degrees.", "problem", "technical", False,
     [("Camera calibration", "method"), ("homography", "concept"), ("AR headset", "platform")],
     [("Camera calibration", "homography", "USES")],
     "which thermal effect broke the AR camera calibration and which startup step stopped compensating",
     "camera calibration homography thermal drift baseline headset"),
    # --- 7 architecture ---
    ("Depth Anything replaced MiDaS in the background-blur pipeline; the relative-depth prior is sharper at object boundaries and the matting pass no longer leaks halo pixels around hair.", "architecture", "technical", False,
     [("Depth Anything", "framework"), ("MiDaS", "framework"), ("matting", "method")],
     [("Depth Anything", "MiDaS", "REPLACES")],
     "which monocular depth model took over from MiDaS for background blur and why did matting improve",
     "depth anything midas matting boundary halo background blur"),
    # --- 8 reference ---
    ("The feature-matching baseline still cites Lowe's 2004 SIFT paper for the ratio test; SIFT stays the reference, and ORB is the deployed fallback on mobile because its binary descriptors fit a tight memory budget.", "reference", "technical", False,
     [("Lowe's 2004 SIFT paper", "publication"), ("SIFT", "algorithm"), ("ORB", "algorithm"), ("ratio test", "method")],
     [("SIFT", "ratio test", "HAS_PART"), ("ORB", "SIFT", "REPLACES")],
     "which classical descriptors anchor the matching baseline and which one ships on mobile",
     "sift orb lowe 2004 ratio test binary descriptor mobile"),
    # --- 9 decision ---
    ("Chose Kornia over raw torchvision transforms for training-time augmentation; keeping everything on the GPU collapsed the CPU data-loader bottleneck that capped the 8-GPU job at sixty percent utilisation.", "decision", "technical", False,
     [("Kornia", "library"), ("torchvision", "library"), ("GPU", "infrastructure")],
     [("Kornia", "torchvision", "REPLACES"), ("Kornia", "GPU", "DEPLOYED_ON")],
     "which augmentation library took over from torchvision transforms and what bottleneck did it clear",
     "kornia torchvision gpu augmentation data loader bottleneck"),
    # --- 10 noise ---
    ("The hallway coffee machine blinked a descale light for three weeks before anyone opened the manual and fed it a citric-acid pouch.", "fact", "noise", True, [], [], None, None),
    # --- 11 architecture ---
    ("Structure-from-motion for the drone survey uses COLMAP for sparse reconstruction followed by Gaussian Splatting for the dense view-synthesis pass; the NeRF path stays only as a quality reference.", "architecture", "technical", False,
     [("COLMAP", "tool"), ("Gaussian Splatting", "method"), ("NeRF", "method"), ("Structure-from-motion", "concept")],
     [("Gaussian Splatting", "NeRF", "REPLACES"), ("COLMAP", "Structure-from-motion", "IMPLEMENTS")],
     "how does the drone reconstruction chain COLMAP into Gaussian Splatting and where does NeRF still fit",
     "colmap gaussian splatting nerf sfm drone dense view synthesis"),
    # --- 12 problem ---
    ("Optical flow with Farneback produced stuttering trails under motion blur; RAFT's iterative refinement fixed the worst stretches but the extra VRAM pushed the real-time target off the Jetson.", "problem", "technical", False,
     [("Farneback", "algorithm"), ("RAFT", "algorithm"), ("Jetson", "platform"), ("VRAM", "infrastructure")],
     [("RAFT", "Farneback", "IMPROVES_ON"), ("RAFT", "Jetson", "DEPLOYED_ON")],
     "which optical-flow method cleaned up the motion-blur trails and what cost did it add on the Jetson",
     "farneback raft optical flow motion blur jetson vram realtime"),
    # --- 13 decision ---
    ("Switched the segmentation codebase from Detectron2 to MMSegmentation; the config-as-python registry pattern slotted into our existing YAML overlays and cut boilerplate on each new backbone.", "decision", "technical", False,
     [("Detectron2", "framework"), ("MMSegmentation", "framework"), ("YAML", "technology")],
     [("MMSegmentation", "Detectron2", "REPLACES")],
     "which segmentation framework replaced Detectron2 and which config pattern drove the migration",
     "mmsegmentation detectron2 config registry yaml backbone"),
    # --- 14 architecture ---
    ("Instance segmentation in production pairs MMDetection's Mask2Former head with the ImageNet-pretrained Swin-L backbone; LVIS-style long tail distilled into the loss as a class-balanced sampler.", "architecture", "technical", False,
     [("MMDetection", "framework"), ("Mask2Former", "algorithm"), ("Swin-L", "algorithm"), ("ImageNet", "publication"), ("LVIS", "publication")],
     [("MMDetection", "Mask2Former", "USES"), ("Swin-L", "ImageNet", "BUILDS_ON")],
     "which head and backbone pair did MMDetection use for production instance segmentation and what long-tail trick shipped",
     "mmdetection mask2former swin l imagenet lvis class balanced"),
    # --- 15 milestone ---
    ("Hit 37.4 mAP on COCO val2017 with the pruned YOLOX-S build; structured channel pruning dropped twenty percent of the parameters while staying within one point of the dense baseline.", "milestone", "technical", False,
     [("YOLOX-S", "algorithm"), ("COCO", "publication"), ("channel pruning", "method")],
     [("YOLOX-S", "channel pruning", "USES")],
     "how close did the pruned YOLOX-S land on COCO val2017 and which compression method drove the win",
     "yolox s coco val2017 channel prune map compression"),
    # --- 16 fact ---
    ("OWL-ViT serves the text-prompted zero-shot detector in the moderation stack; prompt ensembling over three synonym lists trims false positives on ambiguous categories like weapons and tools.", "fact", "technical", False,
     [("OWL-ViT", "framework"), ("prompt ensembling", "method")],
     [("OWL-ViT", "prompt ensembling", "USES")],
     "which zero-shot detector drives the moderation stack and which prompting trick cut false positives",
     "owl vit prompt ensemble zero shot moderation synonym"),
    # --- 17 architecture ---
    ("Image-stitching for the panorama service does feature matching with ORB, homography estimation via RANSAC, then multi-band blending; the old Viola-Jones-based seam finder is retired.", "architecture", "technical", False,
     [("ORB", "algorithm"), ("RANSAC", "algorithm"), ("Viola-Jones", "algorithm"), ("multi-band blending", "method"), ("Image-stitching", "concept")],
     [("ORB", "Viola-Jones", "REPLACES"), ("Image-stitching", "RANSAC", "USES")],
     "how does the panorama stitcher chain ORB matching with RANSAC and which legacy seam finder was dropped",
     "orb ransac viola jones stitch panorama seam blend"),
    # --- 18 decision ---
    ("Went with OpenCV's stereoSGBM for stereo depth over a neural baseline; the semi-global matcher is CPU-only, deterministic across the fleet, and the occlusion-hole count stays in budget for path-planning.", "decision", "technical", False,
     [("OpenCV", "library"), ("stereoSGBM", "algorithm"), ("stereo depth", "concept")],
     [("OpenCV", "stereoSGBM", "IMPLEMENTS"), ("stereoSGBM", "stereo depth", "APPLIES_TO")],
     "why did the stereo depth module pick stereoSGBM over a neural matcher for fleet deployment",
     "opencv stereosgbm stereo depth deterministic cpu occlusion"),
    # --- 19 reference ---
    ("Training references the Open Images v7 dataset for long-tail detector pretraining; its hierarchical labels pair well with the federated classification loss the team lifted from the OpenImages paper.", "reference", "technical", False,
     [("Open Images v7", "publication"), ("federated classification loss", "method"), ("OpenImages paper", "publication")],
     [("federated classification loss", "OpenImages paper", "AUTHORED_BY")],
     "which public dataset seeds long-tail detector pretraining and which loss formulation does it motivate",
     "open images v7 federated classification long tail detector"),
    # --- 20 problem ---
    ("The HOG-based pedestrian detector underperformed on the night dataset; replacing it with a finetuned Ultralytics YOLOv8n cut false negatives in half but the embedded-CPU budget needed INT8 quant to fit.", "problem", "technical", False,
     [("HOG", "algorithm"), ("Ultralytics", "organization"), ("YOLOv8n", "framework"), ("INT8 quant", "method")],
     [("YOLOv8n", "HOG", "REPLACES"), ("YOLOv8n", "INT8 quant", "USES")],
     "which night-time detector swap fixed the HOG false negatives and which compression let it fit the CPU",
     "hog yolov8n ultralytics int8 quant pedestrian night"),
    # --- 21 architecture ---
    ("Camera calibration pipeline uses OpenCV's cv2.calibrateCamera over a printed ChArUco board; Kornia's differentiable projection validates re-projection error in a post-hoc loss for sanity.", "architecture", "technical", False,
     [("OpenCV", "library"), ("cv2.calibrateCamera", "api"), ("ChArUco", "method"), ("Kornia", "library"), ("re-projection error", "concept")],
     [("OpenCV", "cv2.calibrateCamera", "IMPLEMENTS"), ("Kornia", "re-projection error", "PRODUCES")],
     "how does the calibration pipeline split OpenCV's solver from a Kornia reprojection check",
     "opencv calibrate camera charuco kornia reprojection error"),
    # --- 22 decision ---
    ("Zip-NeRF replaced the vanilla NeRF path in the cultural-heritage scanner; anti-aliased sampling and the proposal network killed the flicker on thin-structure surfaces that the original rendering showed.", "decision", "technical", False,
     [("Zip-NeRF", "method"), ("NeRF", "method"), ("proposal network", "concept")],
     [("Zip-NeRF", "NeRF", "REPLACES"), ("Zip-NeRF", "proposal network", "USES")],
     "which neural rendering upgrade fixed the thin-structure flicker on the heritage scanner",
     "zip nerf nerf proposal anti alias flicker heritage"),
    # --- 23 architecture ---
    ("The visual search service runs a DINOv2 encoder into a FAISS IVF index; the EVA-CLIP fallback handles text-query lookups where the DINOv2 embeddings alone can't disambiguate near-duplicate styles.", "architecture", "technical", False,
     [("DINOv2", "framework"), ("FAISS", "library"), ("EVA-CLIP", "framework"), ("IVF", "algorithm")],
     [("DINOv2", "FAISS", "COMMUNICATES_WITH"), ("FAISS", "IVF", "USES")],
     "how does the visual search service split DINOv2 image retrieval from EVA-CLIP text queries",
     "dinov2 faiss ivf eva clip visual search text query"),
    # --- 24 fact ---
    ("COCO's 80-class ontology still anchors the detector regression suite; LVIS is layered on top with its 1203 long-tail classes for rare-category coverage tests.", "fact", "technical", False,
     [("COCO", "publication"), ("LVIS", "publication")],
     [("LVIS", "COCO", "EXTENDS")],
     "which two detection datasets anchor the regression suite and which one covers the rare categories",
     "coco lvis ontology long tail detector regression"),
    # --- 25 milestone ---
    ("Shipped the Gaussian Splatting viewer on WebGPU; render budget stays under 8 ms for a 1-million-splat scene and beats the NeRF baseline that required a server-side render every frame.", "milestone", "technical", False,
     [("Gaussian Splatting", "method"), ("WebGPU", "technology"), ("NeRF", "method")],
     [("Gaussian Splatting", "WebGPU", "DEPLOYED_ON"), ("Gaussian Splatting", "NeRF", "IMPROVES_ON")],
     "which neural-rendering viewer shipped on WebGPU and how did its budget compare to NeRF",
     "gaussian splatting webgpu nerf budget render viewer"),
    # --- 26 preference ---
    ("Team prefers Ultralytics' YOLO CLI over the raw PyTorch training loop for quick detector iteration; the config-first ergonomics keep experiments reproducible without a full Hydra setup.", "preference", "technical", False,
     [("Ultralytics", "organization"), ("YOLO CLI", "tool"), ("PyTorch", "framework"), ("Hydra", "library")],
     [("YOLO CLI", "PyTorch", "PREFERS")],
     "which detector training interface does the team prefer for quick iteration and why not Hydra",
     "ultralytics yolo cli pytorch hydra training iterate"),
    # --- 27 architecture ---
    ("The SAM 2 mask-propagation memory bank caps at eight frames in the live path; beyond that the IoU consistency check drops the oldest embedding and triggers a lightweight re-prompt from the detector.", "architecture", "technical", False,
     [("SAM 2", "framework"), ("memory bank", "concept"), ("IoU consistency check", "method")],
     [("SAM 2", "memory bank", "HAS_PART"), ("SAM 2", "IoU consistency check", "USES")],
     "how does the live SAM 2 path bound its memory bank and recover when the IoU consistency check trips",
     "sam 2 memory bank iou consistency re prompt live path"),
    # --- 28 problem ---
    ("RAFT optical flow diverged on the drone footage once the motion exceeded the training range; bumping the iterative updates from twelve to thirty-two converged but crossed the frame-time budget on the onboard GPU.", "problem", "technical", False,
     [("RAFT", "algorithm"), ("iterative updates", "method"), ("onboard GPU", "infrastructure")],
     [("RAFT", "iterative updates", "USES"), ("RAFT", "onboard GPU", "DEPLOYED_ON")],
     "how did drone-scale motion break RAFT flow and what parameter tweak crossed the onboard GPU budget",
     "raft optical flow drone iteration gpu budget"),
    # --- 29 decision ---
    ("Dropped the Viola-Jones face cascade entirely in favour of a distilled YOLOv10-face; the classical detector still served on the legacy SDK but its false-positive rate on dark skin was unacceptable.", "decision", "technical", False,
     [("Viola-Jones", "algorithm"), ("YOLOv10", "framework"), ("legacy SDK", "platform")],
     [("YOLOv10", "Viola-Jones", "REPLACES")],
     "which face-detection cascade got retired and what fairness issue forced the switch",
     "viola jones yolov10 face detection fairness cascade"),
    # --- 30 reference ---
    ("Matching the paper's claims: the Depth Anything v2 preprint reports 0.106 AbsRel on KITTI with the large backbone, which sits within noise of our reproduction on the lab rig.", "reference", "technical", False,
     [("Depth Anything v2", "publication"), ("KITTI", "publication"), ("AbsRel", "concept")],
     [("Depth Anything v2", "KITTI", "APPLIES_TO")],
     "which monocular-depth paper's KITTI result did the lab reproduce and what metric did it report",
     "depth anything v2 kitti absrel reproduce monocular"),
    # --- 31 architecture ---
    ("The stitching service stores calibration per lens as an OpenCV YAML file; a HomographyHandle abstraction loads it once and lets downstream code compose warps without recomputing the fundamental matrix.", "architecture", "technical", False,
     [("OpenCV", "library"), ("HomographyHandle", "pattern"), ("fundamental matrix", "concept")],
     [("HomographyHandle", "OpenCV", "USES")],
     "how does the stitching service avoid recomputing the fundamental matrix on every warp",
     "opencv homography handle fundamental matrix stitch calibration"),
    # --- 32 decision ---
    ("Standardised on torchvision 0.18's v2 transforms for augmentation APIs; the old v1 compose path was deprecated and the v2 tensor-dict signature cleaned up multi-target pipelines for detection.", "decision", "technical", False,
     [("torchvision", "library"), ("v2 transforms", "api"), ("v1 compose", "api")],
     [("v2 transforms", "v1 compose", "REPLACES")],
     "which torchvision transform API replaced the v1 compose path and why for detection",
     "torchvision v2 transform v1 compose detection tensor dict"),
    # --- 33 fact ---
    ("ImageNet-21k pretraining is still the most reliable initialisation for the Swin-family heads we ship; JFT-300M weights were unavailable publicly and the self-supervised alternatives lagged on fine-grained classes.", "fact", "technical", False,
     [("ImageNet-21k", "publication"), ("Swin", "algorithm"), ("JFT-300M", "publication")],
     [("Swin", "ImageNet-21k", "BUILDS_ON")],
     "which pretraining corpus remains the reliable init for the Swin heads and why not JFT-300M",
     "imagenet 21k swin jft 300m pretrain fine grained"),
    # --- 34 milestone ---
    ("Closed the camera-calibration tooling overhaul: the new Kornia-based rig replaces the OpenCV-only pipeline, and re-projection error on the validation board drops to sub-pixel across all twenty cameras.", "milestone", "technical", False,
     [("Kornia", "library"), ("OpenCV", "library"), ("camera-calibration", "method"), ("re-projection error", "concept")],
     [("Kornia", "OpenCV", "REPLACES"), ("Kornia", "camera-calibration", "IMPLEMENTS")],
     "which Kornia-based rig replaced the OpenCV calibration pipeline and what error target did it hit",
     "kornia opencv calibration reprojection sub pixel camera"),
    # --- 35 preference ---
    ("Preference locked in for MMDetection's config registry over Detectron2's LazyConfig; the inheritance rules compose more cleanly when a single experiment overlays three datasets and two backbones.", "preference", "technical", False,
     [("MMDetection", "framework"), ("Detectron2", "framework"), ("LazyConfig", "api")],
     [("MMDetection", "LazyConfig", "PREFERS")],
     "which detector framework's config system did the team prefer over LazyConfig and why",
     "mmdetection detectron2 lazyconfig registry overlay"),
    # --- 36 problem ---
    ("CLIP text-embedding drift across OpenAI weights and the OpenCLIP re-implementation broke the image-search index; re-embedding the entire corpus on one model version fixed the nearest-neighbour quality.", "problem", "technical", False,
     [("CLIP", "framework"), ("OpenAI", "organization"), ("OpenCLIP", "framework"), ("nearest-neighbour", "algorithm")],
     [("OpenCLIP", "CLIP", "IMPLEMENTS")],
     "which CLIP weight inconsistency broke the search index and what rebuild fixed it",
     "clip openai openclip weight drift index rebuild"),
    # --- 37 architecture ---
    ("Dataset pipeline serialises annotations to COCO JSON for detection and to LVIS JSON for the long-tail split; the converter tool is an Ultralytics fork pinned to the v8.2 tag for stable label indexing.", "architecture", "technical", False,
     [("COCO JSON", "technology"), ("LVIS JSON", "technology"), ("Ultralytics", "organization"), ("v8.2", "date")],
     [("COCO JSON", "LVIS JSON", "RELATED_TO")],
     "how does the dataset pipeline split COCO JSON from LVIS JSON and which converter version is pinned",
     "coco lvis json ultralytics v8 2 converter annotation"),
    # --- 38 reference ---
    ("Segment Anything's 2023 release paper underpins the prompt-encoder decomposition we reuse; SAM 2's 2024 follow-up adds the memory-attention module that makes the video path work.", "reference", "technical", False,
     [("Segment Anything", "publication"), ("SAM 2", "framework"), ("memory-attention", "concept")],
     [("SAM 2", "Segment Anything", "EXTENDS"), ("SAM 2", "memory-attention", "HAS_PART")],
     "which two Segment Anything papers grounded the prompt-encoder and video memory design",
     "segment anything sam 2 memory attention prompt encoder"),
    # --- 39 decision ---
    ("Chose Grounding DINO over OWL-ViT for the text-prompted detector in the retail pilot; the phrase-grounding head handled compositional prompts like 'blue mug with chipped handle' more robustly.", "decision", "technical", False,
     [("Grounding DINO", "framework"), ("OWL-ViT", "framework"), ("phrase-grounding", "method")],
     [("Grounding DINO", "OWL-ViT", "PREFERS"), ("Grounding DINO", "phrase-grounding", "USES")],
     "which text-prompted detector won over OWL-ViT for the retail pilot and which prompt style mattered",
     "grounding dino owl vit phrase grounding retail prompt"),
    # --- 40 architecture ---
    ("Depth Anything v2 feeds a fused-feature head that runs alongside Gaussian Splatting's rasteriser; priors from monocular depth anchor floating splats that the multi-view consistency loss alone couldn't pin.", "architecture", "technical", False,
     [("Depth Anything v2", "framework"), ("Gaussian Splatting", "method"), ("multi-view consistency", "method")],
     [("Gaussian Splatting", "Depth Anything v2", "USES"), ("Gaussian Splatting", "multi-view consistency", "USES")],
     "how does the splatter lean on Depth Anything v2 priors to pin floating splats",
     "depth anything v2 gaussian splatting multi view consistency"),
    # --- 41 fact ---
    ("Farneback flow on OpenCV still powers the thumbnail-motion heuristic; the lightweight dense field is accurate enough at 240p to drive a highlight-reel selector without a GPU in the loop.", "fact", "technical", False,
     [("Farneback", "algorithm"), ("OpenCV", "library"), ("highlight-reel", "pattern")],
     [("OpenCV", "Farneback", "IMPLEMENTS")],
     "which OpenCV flow method drives the thumbnail-motion heuristic without a GPU in the loop",
     "farneback opencv thumbnail motion highlight 240p cpu"),
    # --- 42 decision ---
    ("Dropped ONNX export of the DETR variants; TensorRT plugins for the deformable-attention op lagged upstream, so we pinned the deployment to plain PyTorch with torch.compile for the GPU path.", "decision", "technical", False,
     [("ONNX", "technology"), ("DETR", "framework"), ("TensorRT", "framework"), ("PyTorch", "framework"), ("torch.compile", "api"), ("deformable-attention", "algorithm")],
     [("PyTorch", "ONNX", "REPLACES"), ("PyTorch", "torch.compile", "USES")],
     "why did the team drop ONNX export for DETR and which PyTorch path took over",
     "onnx detr tensorrt pytorch torch compile deformable attention"),
    # --- 43 noise ---
    ("Someone left a tupperware of lasagna in the fridge labelled 'do not touch' in three languages and a biohazard sticker showed up by Friday.", "fact", "noise", True, [], [], None, None),
    # --- 44 milestone ---
    ("Shipped the SAM 2 video-tracking demo with 30 fps on an RTX 4090; the cached prompt-encoder outputs per object and the pruned memory-attention kernel were the two biggest wins.", "milestone", "technical", False,
     [("SAM 2", "framework"), ("RTX 4090", "infrastructure"), ("memory-attention", "concept")],
     [("SAM 2", "RTX 4090", "DEPLOYED_ON"), ("SAM 2", "memory-attention", "USES")],
     "what hardware and kernel tweaks let the SAM 2 video demo hit 30 fps",
     "sam 2 rtx 4090 memory attention video 30 fps kernel"),
    # --- 45 problem ---
    ("Homography estimation drifted when the planar assumption broke on the warehouse-floor panorama; switching from RANSAC-homography to MAGSAC++ with a fundamental-matrix model cut the outlier rate by a third.", "problem", "technical", False,
     [("homography", "concept"), ("RANSAC", "algorithm"), ("MAGSAC++", "algorithm"), ("fundamental-matrix", "concept")],
     [("MAGSAC++", "RANSAC", "IMPROVES_ON")],
     "which robust estimator replaced RANSAC-homography once the warehouse floor violated the planar model",
     "homography ransac magsac fundamental matrix outlier warehouse"),
    # --- 46 reference ---
    ("Tracking the DINOv2 follow-up paper for the registered-tokens improvement; the registered-tokens trick damped the high-norm artefact tokens that poisoned dense-prediction heads in the original release.", "reference", "technical", False,
     [("DINOv2", "framework"), ("registered-tokens", "method"), ("high-norm artefact", "finding")],
     [("DINOv2", "registered-tokens", "USES"), ("registered-tokens", "high-norm artefact", "FIXES")],
     "which DINOv2 follow-up trick damped the high-norm artefact tokens hurting dense heads",
     "dinov2 registered tokens high norm artefact dense"),
    # --- 47 preference ---
    ("Prefer Kornia's LightGlue wrapper over raw SuperPoint+LoFTR plumbing for feature matching; the end-to-end callable keeps the batch dimension consistent with the rest of the augmentation pipeline.", "preference", "technical", False,
     [("Kornia", "library"), ("LightGlue", "algorithm"), ("SuperPoint", "algorithm"), ("LoFTR", "algorithm")],
     [("Kornia", "LightGlue", "USES"), ("LightGlue", "SuperPoint", "PREFERS")],
     "which Kornia matcher does the team prefer over raw SuperPoint plus LoFTR and why",
     "kornia lightglue superpoint loftr matcher batch pipeline"),
    # --- 48 architecture ---
    ("The SfM reconstruction queue offloads dense matching to GPU workers running hloc; COLMAP handles the bundle-adjustment refinement at the end and writes a standard .bin model that the viewer ingests.", "architecture", "technical", False,
     [("SfM", "concept"), ("hloc", "tool"), ("COLMAP", "tool"), ("bundle-adjustment", "method"), (".bin", "file")],
     [("COLMAP", "bundle-adjustment", "IMPLEMENTS"), ("hloc", "COLMAP", "COMMUNICATES_WITH")],
     "how does the SfM queue split dense matching with hloc from COLMAP's bundle-adjustment stage",
     "sfm hloc colmap bundle adjustment bin dense match"),
    # --- 49 preference ---
    ("For detection demos we lean on Ultralytics YOLOv8 over MMDetection; the one-file train command and cleaner CLI beats the registry indirection for a five-minute screen-share.", "preference", "technical", False,
     [("Ultralytics", "organization"), ("YOLOv8", "framework"), ("MMDetection", "framework")],
     [("YOLOv8", "MMDetection", "PREFERS")],
     "which detector stack do we prefer for demos and what CLI trait beat MMDetection's registry",
     "ultralytics yolov8 mmdetection demo cli registry"),
    # --- 50 reference ---
    ("The 2023 Gaussian Splatting paper, '3D Gaussian Splatting for Real-Time Radiance Field Rendering,' grounds our splatter; Zip-NeRF's 2023 paper still informs the anti-aliasing tricks we ported into the rasteriser.", "reference", "technical", False,
     [("Gaussian Splatting", "method"), ("3D Gaussian Splatting for Real-Time Radiance Field Rendering", "publication"), ("Zip-NeRF", "method")],
     [("Gaussian Splatting", "3D Gaussian Splatting for Real-Time Radiance Field Rendering", "AUTHORED_BY"), ("Gaussian Splatting", "Zip-NeRF", "BUILDS_ON")],
     "which two 2023 papers underpin the team's splatter and its anti-aliasing port",
     "gaussian splatting zip nerf radiance field anti alias paper"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
