# -*- coding: utf-8 -*-
"""TransferLearning.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1YWmMjjVpLARrJKWWgTAORqKjM_s2RMVM

### PyTorch tutorial #1  
## TRANSFER LEARNING

Transfer learning is a machine learning method where a model developed for the first task is then used as the starting point for a model on a second task. Since it is relatively rare to have a dataset of sufficient size, in practice very few people train an entire CNN from scratch and it is common to pretrain a ConvNet on a very large dataset (ImageNet) and then use the ConvNet either as an initialization or a fixed feature extractor for the task of interest.


In This tutorial uses a subset of ImageNet as a dataset and a ResNet as the architecture.

Sources for this tutorial:
- [PyTorch Official Website](https://pytorch.org/tutorials/beginner/transfer_learning_tutorial.html)
- [Video Explanation](https://www.youtube.com/watch?v=t6oHGXt04ik)
"""

from __future__ import print_function, division
#A future statement is a directive to the compiler that a particular module should be compiled 
#using syntax or semantics that will be available in a specified future release of Python where the feature becomes standard.
#A future statement must appear near the top of the module.

import torch
import torch.nn as nn  #Contains the neural network layers
import torch.optim as optim  #A package implementing various optimization algorithms
from torch.optim import lr_scheduler  #A Learning rate schedule is a predefined framework that 
#adjusts the learning rate between epochs or iterations as the training progresses
import torch.backends.cudnn as cudnn  #torch.backends controls the behavior of various backends that PyTorch supports.
import numpy as np
import torchvision  #Torchvision provides many built-in datasets in the torchvision.datasets module,
#as well as utility classes for building your own datasets.
from torchvision import datasets, models, transforms
import matplotlib.pyplot as plt #a collection of command style functions that make matplotlib work like MATLAB.
import time #Python time module allows to work with time in Python
import os #provides functions for creating and removing a directory (folder), fetching its contents,
# changing and identifying the current directory, etc.
import copy #It means that any changes made to a copy of object do reflect in the original object.

cudnn.benchmark = True 
#This flag allows you to enable the inbuilt cudnn auto-tuner to find the best algorithm to use for your hardware.
#Use it if your model does not change and your input sizes remain the same

plt.ion()
# turns on the interactive mode of matplotlib.pyplot, in which the graph display gets updated after each statement.

"""## The Problem
Train a model to classify ants and bees. We have about 120 training images each for ants and bees. There are 75 validation images for each class. Usually, this is a very small dataset to generalize upon, if trained from scratch. Since we are using transfer learning, the network has already learnet useful features and we should be able to generalize reasonably well.

### Data Augmentation & Normalization

- ### *transformers.compose* 
To chain the transformers together
- ### *transforms.RandomResizedCrop ( size, scale, ratio, interpolation)*  
Crop a random portion of image and resize it to a given size. 
  - size (int or sequence): expected output size of the crop, for each edge.
  - scale (tuple of python:float): Specifies the lower and upper bounds for the random area of the crop, before resizing. The scale is defined with respect to the area of the original image.
  - ratio (tuple of python:float): lower and upper bounds for the random aspect ratio of the crop, before resizing.
  - interpolation (InterpolationMode) ??? Desired interpolation enum defined by torchvision.transforms.InterpolationMode. Default is InterpolationMode.BILINEAR
- ### *transforms.RandomHorizontalFlip(p)*
  Horizontally flip the given image randomly with a given probability p. 
- ### *transforms.ToTensor()*
Transforms images loaded by Pillow into PyTorch tensors
- ### *transforms.Normalize(mean, std, inplace=False)*
Normalize a tensor image with mean and standard deviation. Not necessary, but helps the model to preform better.
  - mean (sequence): Sequence of means for each channel.
  - std (sequence): Sequence of standard deviations for each channel.
  - inplace (bool,optional): Bool to make this operation in-place.
- ### *transforms.Resize(size, interpolation=<InterpolationMode.BILINEAR: 'bilinear'>, max_size=None, antialias=None)*
Resize the input image to the given size.
  - size (sequence or int): Desired output size. 
  - interpolation (InterpolationMode): Desired interpolation enum defined by torchvision.transforms.InterpolationMode. 
  - max_size (int, optional): The maximum allowed for the longer edge of the resized image
  - antialias (bool, optional): antialias flag. If img is PIL Image, the flag is ignored and anti-alias is always used. If img is Tensor, the flag is False by default and can be set to True for InterpolationMode.BILINEAR only mode. This can help making the output for PIL images and tensors closer.
- ### *transforms.CenterCrop(size)*
Crops the given image at the center.
  - size (sequence or int): Desired output size of the crop. If size is an int instead of sequence like (h, w), a square crop (size, size) is made.
"""

# Data augmentation and normalization for training
# Just normalization for validation
data_transforms = {
    'train' : transforms.Compose([
                                  transforms.RandomResizedCrop(224), #augmenting
                                  transforms.RandomHorizontalFlip(), #augmenting
                                  transforms.ToTensor(), #pytorch can read it now
                                  transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
                                  ]), #mean and std for 3 channels of RGB
    'val' : transforms.Compose([
                                transforms.Resize(256),
                                transforms.CenterCrop(224), #to get the actual object to classify
                                transforms.ToTensor(),
                                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ]),
}

#Add the dataset to the google drive and mount it.
data_dir = '/content/drive/MyDrive/Colab Notebooks/hymenoptera_data'

"""## Loading The Data
This [dataset](https://download.pytorch.org/tutorial/hymenoptera_data.zip) is a very small subset of imagenet. Use torchvision and torch.utils.data packages for loading the data. 

You have the `train` and `val` images and you pass in the path and transforms for each of them.

- ### *torchvision.datasets.ImageFolder()*  
A generic data loader
   - root (string): Root directory path.
   - transform (callable, optional): A function/transform that takes in an PIL image and returns a transformed version. E.g, transforms.RandomCrop
   - target_transform (callable, optional): A function/transform that takes in the target and transforms it.
- ### *os.path.join(path, *paths)*  
os.path module implements some useful functions on pathnames. Here it joins one or more path components intelligently.
"""

image_datasets = {x: datasets.ImageFolder(os.path.join(data_dir, x),
                                          data_transforms[x])
                  for x in ['train', 'val']} #creating a dictionary

image_datasets["val"] #to see the information

"""### Setting up the data loaders
- ### *torch.utils.data.DataLoader*  
Combines a dataset and a sampler, and provides an iterable over the given dataset.

  - *batch_size=4*

    4 will work well since our dataset is small.

  - *shuffle=True*
  
    usually we turn the shuffle on because we want to shuffle data in every epoch so it doesn't learn the same pattern.(Makes the model more robust)
    - *num_workers*

    Number of subprocesses that are running. This will speed up the data loader.

"""

dataloaders = {x: torch.utils.data.DataLoader(image_datasets[x], batch_size=4,
                                             shuffle=True, num_workers=4)
              for x in ['train', 'val']}

"""- ### *torch.device*. 
An object representing the device on which a torch.Tensor is or will be allocated.(('cpu' or 'cuda'))
"""

dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'val']}
class_names = image_datasets['train'].classes

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

"""## Visualizing a few images

Visualizing a few training images so as to understand the data augmentations.

- ### *next(iter(dataloaders))*
makes dataloader object to be a iterable and ???next??? helps it to iterate over it.
If your Dataset.__getitem__ returns multiple tensors, next(iter(loader)) will return a batch for each output.
- ### *torchvision.utils.make_grid(tensor: Union[torch.Tensor, List[torch.Tensor]], nrow: int = 8, padding: int = 2, normalize: bool = False, value_range: Optional[Tuple[int, int]] = None, scale_each: bool = False, pad_value: float = 0.0, **kwargs)*
Make a grid of images.
  - tensor (Tensor or list): 4D mini-batch Tensor of shape (B x C x H x W) or a list of images all of the same size.
  - nrow (int, optional):  Number of images displayed in each row of the grid. The final grid size is (B / nrow, nrow). Default: 8.
  - padding (int, optional): amount of padding. Default: 2
  - normalize (bool, optional): If True, shift the image to the range (0, 1), by the min and max values specified by value_range. Default: False.
  - value_range (tuple, optional): tuple (min, max) where min and max are numbers, then these numbers are used to normalize the image. By default, min and max are computed from the tensor.
  - range (tuple. optional)
  - scale_each (bool, optional): If True, scale each image in the batch of images separately rather than the (min, max) over all images. Default: False.
  - pad_value (float, optional): Value for the padded pixels. Default: 0.




"""

def imshow(inp, title=None):
    """Imshow for Tensor."""
    inp = inp.numpy().transpose((1, 2, 0)) #transposes the data (x,y,z)->(y,z,x)
    mean = np.array([0.485, 0.456, 0.406]) # Creates an array.
    std = np.array([0.229, 0.224, 0.225])
    inp = std * inp + mean
    inp = np.clip(inp, 0, 1) #Clip (limit) the values in an array.
    plt.imshow(inp)
    if title is not None:
        plt.title(title)
    plt.pause(0.001)  # pause a bit so that plots are updated


# Get a batch of training data
inputs, classes = next(iter(dataloaders['train']))

# Make a grid from batch
out = torchvision.utils.make_grid(inputs)

imshow(out, title=[class_names[x] for x in classes])

"""## Training the model
A general function to train a model.

- ### *best_model_wts = copy.deepcopy(model.state_dict())*
will take a copy of the original object and will then recursively take a copy of the inner objects, i.e. all parameters of your model. The model structure will not be saved.

- ### *optim.Optimizer.zero_grad(set_to_none=False)*
Sets the gradients of all optimized torch.Tensor s to zero.
  - *set_to_none=False*: instead of setting to zero, set the grads to None.
"""

def train_model(model, criterion, optimizer, scheduler, num_epochs=25):
    since = time.time()
    #Returns the time in seconds since the epoch.

    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0

    for epoch in range(num_epochs):
        print(f'Epoch {epoch}/{num_epochs - 1}')
        print('-' * 10)

        # Each epoch has a training and validation phase
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()  # Set model to training mode
            else:
                model.eval()   # Set model to evaluate mode

            running_loss = 0.0
            running_corrects = 0

            # Iterate over data.
            for inputs, labels in dataloaders[phase]:
                inputs = inputs.to(device)
                #uses a copy of inputs that resides on device.
                labels = labels.to(device)

                # zero the parameter gradients
                optimizer.zero_grad()

                # forward
                # track history if only in train
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    # backward + optimize only if in training phase
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                # statistics
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
            if phase == 'train':
                scheduler.step()

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]

            print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

            # deep copy the model
            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())

        print()

    time_elapsed = time.time() - since
    print(f'Training complete in {time_elapsed // 60:.0f}m {time_elapsed % 60:.0f}s')
    print(f'Best val Acc: {best_acc:4f}')

    # load best model weights
    model.load_state_dict(best_model_wts)
    return model

"""## Visualizing the model predictions

Generic function to display predictions for a few images
"""

def visualize_model(model, num_images=6):
    was_training = model.training
    model.eval()
    images_so_far = 0
    fig = plt.figure()

    with torch.no_grad():
        for i, (inputs, labels) in enumerate(dataloaders['val']):
            inputs = inputs.to(device)
            labels = labels.to(device)

            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)

            for j in range(inputs.size()[0]):
                images_so_far += 1
                ax = plt.subplot(num_images//2, 2, images_so_far)
                ax.axis('off')
                ax.set_title(f'predicted: {class_names[preds[j]]}')
                imshow(inputs.cpu().data[j])

                if images_so_far == num_images:
                    model.train(mode=was_training)
                    return
        model.train(mode=was_training)