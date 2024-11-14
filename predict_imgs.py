import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from functools import partial
from nougat import NougatModel
import argparse
import os
import time

class ImageDataset(Dataset):
    def __init__(self, image_paths, preprocess_fn):
        self.image_paths = image_paths
        self.preprocess_fn = preprocess_fn

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        image = Image.open(self.image_paths[idx])
        target_width = 876
        original_width, original_height = image.size

        new_height = int((target_width / original_width) * original_height)

        #image = image.resize((target_width, new_height), Image.Resampling.LANCZOS)
        image_tensor = self.preprocess_fn(image)
        return image_tensor, os.path.basename(self.image_paths[idx])

def main(model_path, input_dir, output_dir, batch_size, gpu_id):
    model = NougatModel.from_pretrained(model_path)
    model.eval()

    device = torch.device(f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu")
    model.to(device)

    preprocess_fn = partial(model.encoder.prepare_input, random_padding=False)

    image_paths = [os.path.join(input_dir, fname) for fname in os.listdir(input_dir)]

    image_dataset = ImageDataset(image_paths, preprocess_fn)
    dataloader = DataLoader(image_dataset, batch_size=batch_size, shuffle=False)

    os.makedirs(output_dir, exist_ok=True)

    total_inference_time = 0

    for batch, filenames in dataloader:
        batch = batch.to(device)
        start_time = time.time()
        output = model.inference(image_tensors=batch, early_stopping=False)
        inference_time = time.time() - start_time
        total_inference_time += inference_time

        predictions = output['predictions']
        token_sequences = output['sequences']
        
        for filename, prediction, token_sequence in zip(filenames, predictions, token_sequences):
            print(prediction)
            clean_token_sequence = [t for t in token_sequence.tolist() if t not in (0, 1)]
            print(f"token length: {len(clean_token_sequence)}")
            output_path = os.path.join(output_dir, filename.replace('.png', '.txt'))
            # with open(output_path, 'w') as f:
            #     f.write(prediction)
            #     f.write(str(len(clean_token_sequence)))

    print(f"Total inference time: {total_inference_time:.2f} seconds")
    print(f"Average inference time per image: {total_inference_time / len(image_paths):.2f} seconds")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch infer images with NougatModel.")
    parser.add_argument('--model_path', type=str, required=True, help="Path to the pretrained model.")
    parser.add_argument('--input_dir', type=str, required=True, help="Directory containing input images.")
    parser.add_argument('--output_dir', type=str, required=True, help="Directory to save output predictions.")
    parser.add_argument('--batch_size', type=int, default=4, help="Batch size for inference.")
    parser.add_argument('--gpu_id', type=int, default=0, help="ID of the GPU to use for inference.")

    args = parser.parse_args()

    main(args.model_path, args.input_dir, args.output_dir, args.batch_size, args.gpu_id)


