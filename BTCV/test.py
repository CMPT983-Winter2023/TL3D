# Copyright 2020 - 2022 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import os

import nibabel as nib
import numpy as np
import torch
from utils.data_utils import get_loader
from utils.utils import dice, resample_3d

#from monai.inferers import sliding_window_inference
from utils.utils import sliding_window_inference
#from monai.networks.nets import SwinUNETR
from models.model import SwinUNETR

'''from medclip import MedCLIPModel, MedCLIPVisionModelViT, MedCLIPProcessor
import nibabel as nib
import numpy as np

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

organs = {1: "spleen",
          2: "right kidney",
          3: "left kidney",
          4: "gallbladder",
          5: "esophagus",
          6: "liver",
          7: "stomach",
          8: "aorta",
          9: "inferior vena cava",
          10: "portal vein and splenic vein",
          11: "pancreas",
          12: "right adrenal gland",
          13: "left adrenal gland"}

processor = MedCLIPProcessor()
medclip_model = MedCLIPModel(vision_cls=MedCLIPVisionModelViT)
medclip_model.from_pretrained()
medclip_model.to(device)

def to_medclip(label):
    label_unique = torch.unique(label)
    text = []
    for label in label_unique:
        if label != 0:
            text.append(organs[int(label)])
    text = ", ".join(text)
    inputs = processor(text=[text], return_tensors="pt", padding=True)
    text_embeds = medclip_model.encode_text(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"])
    #text_embeds = torch.rand(1, 512)
    return text_embeds'''

text_path = os.path.join("./dataset", "Abdomen", "text")

def random_aug(batch_target, valid=False, sw_batch_size=4):
    targets = []
    texts = []
    for target in batch_target:
        target_unique = torch.unique(target)
        target_unique = [int(x.item()) for x in target_unique if int(x.item()) != 0]
        n = np.random.randint(0, 14)
        classes = range(1, 14)
        mask = np.sort(np.random.choice(classes, size=n, replace=False))
        mask = torch.from_numpy(mask)
        target = torch.where(torch.isin(target, mask), torch.tensor(0), target)
        if 0 <= n < 13:
            text = torch.load(os.path.join(text_path, "_".join(str(x) for x in target_unique if x not in mask) + ".pt"))
        elif n == 13:
            text = torch.load(os.path.join(text_path, "0.pt"))    
        targets.append(target.unsqueeze(0))
        texts.append(text)
    texts = torch.concatenate(texts, axis=0)
    if valid:
        texts = texts.repeat(sw_batch_size, 1)
    #return torch.concatenate(targets, axis=0), texts
    return batch_target, texts

parser = argparse.ArgumentParser(description="Swin UNETR segmentation pipeline")
parser.add_argument(
    #"--pretrained_dir", default="./runs/", type=str, help="pretrained checkpoint directory"
    "--pretrained_dir", default="./pretrained_models/", type=str, help="pretrained checkpoint directory"
)
parser.add_argument("--data_dir", default="./dataset/", type=str, help="dataset directory")
parser.add_argument("--exp_name", default="test1", type=str, help="experiment name")
parser.add_argument("--json_list", default="dataset.json", type=str, help="dataset json file")
parser.add_argument(
    "--pretrained_model_name",
    #default="swin_unetr.base_5000ep_f48_lr2e-4_pretrained.pt",
    default="swin_unetr_base.pt",
    #default="model_final.pt",
    type=str,
    help="pretrained model name",
)
parser.add_argument("--feature_size", default=48, type=int, help="feature size")
parser.add_argument("--infer_overlap", default=0.5, type=float, help="sliding window inference overlap")
parser.add_argument("--in_channels", default=1, type=int, help="number of input channels")
parser.add_argument("--out_channels", default=14, type=int, help="number of output channels")
parser.add_argument("--a_min", default=-175.0, type=float, help="a_min in ScaleIntensityRanged")
parser.add_argument("--a_max", default=250.0, type=float, help="a_max in ScaleIntensityRanged")
parser.add_argument("--b_min", default=0.0, type=float, help="b_min in ScaleIntensityRanged")
parser.add_argument("--b_max", default=1.0, type=float, help="b_max in ScaleIntensityRanged")
parser.add_argument("--space_x", default=1.5, type=float, help="spacing in x direction")
parser.add_argument("--space_y", default=1.5, type=float, help="spacing in y direction")
parser.add_argument("--space_z", default=2.0, type=float, help="spacing in z direction")
parser.add_argument("--roi_x", default=96, type=int, help="roi size in x direction")
parser.add_argument("--roi_y", default=96, type=int, help="roi size in y direction")
parser.add_argument("--roi_z", default=96, type=int, help="roi size in z direction")
parser.add_argument("--dropout_rate", default=0.0, type=float, help="dropout rate")
parser.add_argument("--distributed", action="store_true", help="start distributed training")
parser.add_argument("--workers", default=8, type=int, help="number of workers")
parser.add_argument("--RandFlipd_prob", default=0.2, type=float, help="RandFlipd aug probability")
parser.add_argument("--RandRotate90d_prob", default=0.2, type=float, help="RandRotate90d aug probability")
parser.add_argument("--RandScaleIntensityd_prob", default=0.1, type=float, help="RandScaleIntensityd aug probability")
parser.add_argument("--RandShiftIntensityd_prob", default=0.1, type=float, help="RandShiftIntensityd aug probability")
parser.add_argument("--spatial_dims", default=3, type=int, help="spatial dimension of input data")
parser.add_argument("--use_checkpoint", action="store_true", help="use gradient checkpointing to save memory")
parser.add_argument("--concat", action="store_true", help="use concatenation")
parser.add_argument("--contrast", action="store_true", help="use contrastive loss")
parser.add_argument("--attention", action="store_true", help="use attention")
parser.add_argument("--test_mode", default=True, type=bool, help="testing")

def main():
    args = parser.parse_args()
    args.test_mode = True
    output_directory = "./outputs/" + args.exp_name
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    val_loader = get_loader(args)
    pretrained_dir = args.pretrained_dir
    model_name = args.pretrained_model_name
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pretrained_pth = os.path.join(pretrained_dir, model_name)

    if args.concat:
        concat = True
    else:
        concat = False
    if args.contrast:
        contrast = True
    else:
        contrast = False
    if args.attention:
        attention = True
    else:
        attention = False
        
    model = SwinUNETR(
        img_size=96,
        in_channels=args.in_channels,
        out_channels=args.out_channels,
        feature_size=args.feature_size,
        drop_rate=0.0,
        attn_drop_rate=0.0,
        dropout_path_rate=0.0,
        use_checkpoint=args.use_checkpoint,
        concat=concat,
        contrast=contrast,
        attention=attention
    )
    model_dict = torch.load(pretrained_pth)["state_dict"]
    if "model.pt" not in args.pretrained_model_name and args.concat:
        model_dict["decoder5.transp_conv.conv.weight"] = model_dict["decoder5.transp_conv.conv.weight"].repeat(2, 1, 1, 1, 1)
    model.load_state_dict(model_dict)
    model.eval()
    model.to(device)

    with torch.no_grad():
        dice_list_case = []
        for i, batch in enumerate(val_loader):
            #val_inputs, val_labels = (batch["image"].cuda(), batch["label"].cuda())
            val_inputs, val_labels = (batch["image"], batch["label"])
            #val_labels, text = random_aug(val_labels, valid=True, sw_batch_size=4)
            _, text = random_aug(val_labels, valid=True, sw_batch_size=4)
            val_inputs, val_labels, text = val_inputs.cuda(), val_labels.cuda(), text.cuda()
            #text = torch.load(batch["image_meta_dict"]["filename_or_obj"][0].replace("img", "text").replace("nii.gz", "pt")).cuda()
            original_affine = batch["label_meta_dict"]["affine"][0].numpy()
            _, _, h, w, d = val_labels.shape
            target_shape = (h, w, d)

            img_name = batch["image_meta_dict"]["filename_or_obj"][0].split("/")[-1]
            print("Inference on case {}".format(img_name))
            val_outputs = sliding_window_inference(
                val_inputs, (args.roi_x, args.roi_y, args.roi_z), 4, model, overlap=args.infer_overlap, mode="gaussian"
                , text_in=text)

            val_outputs = torch.softmax(val_outputs, 1).cpu().numpy()
            val_outputs = np.argmax(val_outputs, axis=1).astype(np.uint8)[0]
            val_labels = val_labels.cpu().numpy()[0, 0, :, :, :]
            val_outputs = resample_3d(val_outputs, target_shape)
            dice_list_sub = []
            for i in range(1, 14):
                organ_Dice = dice(val_outputs == i, val_labels == i)
                dice_list_sub.append(organ_Dice)
            mean_dice = np.mean(dice_list_sub)
            print("Mean Organ Dice: {}".format(mean_dice))
            dice_list_case.append(mean_dice)
            nib.save(
                nib.Nifti1Image(val_outputs.astype(np.uint8), original_affine), os.path.join(output_directory, img_name)
            )

        print("Overall Mean Dice: {}".format(np.mean(dice_list_case)))


if __name__ == "__main__":
    main()
