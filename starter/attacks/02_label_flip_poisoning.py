"""
Label-Flip Data Poisoning Attack

Copies the balanced dataset and flips a percentage of training labels
(moves images between receipt/non_receipt folders) to degrade model accuracy.

Usage:
    python 02_label_flip_poisoning.py
    python 02_label_flip_poisoning.py --flip-rate 0.10
"""
import os
import shutil
import random
import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
CLASSES = ["receipt", "non_receipt"]
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", "02_label_flip")


def poison_dataset(source_root, target_root, flip_ratio=0.05, seed=42):
    """
    Copy dataset and flip a percentage of training labels.

    Label flipping works by moving images between class folders:
    - A receipt image moved to non_receipt/ gets a flipped label
    - A non_receipt image moved to receipt/ gets a flipped label

    Only training labels are flipped — the test set stays clean so we can
    measure the true impact of poisoning on model performance.

    Args:
        source_root: Path to clean balanced dataset
        target_root: Path for poisoned dataset output
        flip_ratio: Fraction of training labels to flip (default 0.05 = 5%)
        seed: Random seed for reproducibility
    """
    random.seed(seed)

    # Step 1: Copy the entire clean dataset to target
    if os.path.exists(target_root):
        shutil.rmtree(target_root)
    shutil.copytree(source_root, target_root)

    # Only the TRAINING split is poisoned; the test set is left untouched.
    opposite = {"receipt": "non_receipt", "non_receipt": "receipt"}

    # Snapshot the clean per-class file lists BEFORE moving anything, so that
    # files flipped into a folder are never re-selected for a second flip.
    train_files = {}
    for class_name in CLASSES:
        class_dir = os.path.join(target_root, "train", class_name)
        train_files[class_name] = [
            f for f in os.listdir(class_dir)
            if os.path.isfile(os.path.join(class_dir, f))
            and os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
        ]

    total_train = sum(len(files) for files in train_files.values())
    total_flipped = 0

    for class_name in CLASSES:
        files = train_files[class_name]
        n_flip = int(len(files) * flip_ratio)
        if n_flip == 0:
            continue

        to_flip = random.sample(files, n_flip)
        src_dir = os.path.join(target_root, "train", class_name)
        dst_dir = os.path.join(target_root, "train", opposite[class_name])

        for fname in to_flip:
            src = os.path.join(src_dir, fname)
            # Prefix encodes the ORIGINAL label so visualize_flip() can pair it
            # back to the clean source image, and avoids name collisions.
            dst = os.path.join(dst_dir, f"flipped_{class_name}_{fname}")
            shutil.move(src, dst)
            total_flipped += 1

        print(f"[train] {class_name}: flipped {n_flip}/{len(files)} "
              f"-> {opposite[class_name]}")

    actual_rate = total_flipped / total_train if total_train else 0.0
    print(f"\nTotal training images: {total_train}")
    print(f"Labels flipped: {total_flipped} ({actual_rate:.2%})")

    print("\nImage counts per split/class after poisoning:")
    for split in ["train", "test"]:
        for class_name in CLASSES:
            class_dir = os.path.join(target_root, split, class_name)
            count = len([
                f for f in os.listdir(class_dir)
                if os.path.isfile(os.path.join(class_dir, f))
                and os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
            ]) if os.path.isdir(class_dir) else 0
            print(f"  {split}/{class_name}: {count}")

    print(f"\nPoisoned dataset created at {target_root}")
    return {
        "total_train": total_train,
        "total_flipped": total_flipped,
        "flip_ratio": actual_rate,
    }


def visualize_flip(source_root, target_root, num_images=5, output_dir=RESULTS_DIR, seed=42):
    """Save a grid showing clean labels beside their flipped poisoned labels."""
    flipped_samples = []

    for poisoned_label in CLASSES:
        poisoned_dir = os.path.join(target_root, "train", poisoned_label)
        if not os.path.isdir(poisoned_dir):
            continue

        for filename in os.listdir(poisoned_dir):
            poisoned_path = os.path.join(poisoned_dir, filename)
            if (
                not os.path.isfile(poisoned_path)
                or os.path.splitext(filename)[1].lower() not in IMAGE_EXTENSIONS
            ):
                continue

            original_label = None
            original_filename = None
            for cls in CLASSES:
                prefix = f"flipped_{cls}_"
                if filename.startswith(prefix):
                    original_label = cls
                    original_filename = filename[len(prefix):]
                    break

            if original_label is None:
                continue

            clean_path = os.path.join(
                source_root,
                "train",
                original_label,
                original_filename,
            )
            if os.path.exists(clean_path):
                flipped_samples.append({
                    "clean_path": clean_path,
                    "poisoned_path": poisoned_path,
                    "original_label": original_label,
                    "poisoned_label": poisoned_label,
                    "filename": original_filename,
                })

    if not flipped_samples:
        print("No flipped images found to visualize.")
        return None

    rng = random.Random(seed)
    sample_count = min(num_images, len(flipped_samples))
    samples = rng.sample(flipped_samples, sample_count)

    fig, axes = plt.subplots(sample_count, 2, figsize=(8, 3 * sample_count))
    if sample_count == 1:
        axes = [axes]

    for row, sample in enumerate(samples):
        clean_img = plt.imread(sample["clean_path"])
        poisoned_img = plt.imread(sample["poisoned_path"])

        axes[row][0].imshow(clean_img)
        axes[row][0].set_title(
            f"Clean: {sample['original_label']}\n{sample['filename']}",
            fontsize=9,
        )
        axes[row][0].axis("off")

        axes[row][1].imshow(poisoned_img)
        axes[row][1].set_title(
            f"Flipped label: {sample['poisoned_label']}\n"
            f"from {sample['original_label']}",
            fontsize=9,
        )
        axes[row][1].axis("off")

    fig.suptitle(
        f"Label Flip Poisoning Samples ({sample_count} images)",
        fontsize=12,
    )
    fig.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"label_flip_results_{sample_count}.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"Label flip visualization saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Label-Flip Poisoning Attack")
    parser.add_argument(
        "--source",
        default=os.path.join(os.path.dirname(__file__),
                             "..", "classifier", "balanced_data"),
    )
    parser.add_argument(
        "--target",
        default=os.path.join(os.path.dirname(__file__),
                             "..", "classifier", "poisoned_data"),
    )
    parser.add_argument("--flip-rate", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--visualize-count", type=int, default=5)
    parser.add_argument("--results-dir", default=RESULTS_DIR)
    args = parser.parse_args()

    poison_dataset(args.source, args.target, args.flip_rate, args.seed)
    visualize_flip(
        args.source,
        args.target,
        num_images=args.visualize_count,
        output_dir=args.results_dir,
        seed=args.seed,
    )
