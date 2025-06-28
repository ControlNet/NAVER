import tensorneko as N
import argparse
import torch

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=str, default="result.jsonl")
args = parser.parse_args()

ious = []
accs = []
err = 0
success = 0
for each in N.io.read.json.of_jsonl(args.input):
    if "iou" not in each:
        try:
            iou = N.evaluation.iou_2d(
                torch.tensor(eval(each["result"])["final_answer"][:4]),
                torch.tensor([each["ground_truth"]]),
            )[0, 0].item()
        except TypeError:
            err += 1
            continue
        except KeyError:
            iou = 0
    else:
        iou = each["iou"]
        if iou is None:
            err += 1
            continue
    success += 1
    accs.append(1 if iou > 0.5 else 0)
    ious.append(iou)

print(f"mean IoU: {sum(ious) / len(ious)}")
print(f"Accuracy: {sum(accs) / len(accs)}")
print(f"Error rate: {err / (success + err)}")
