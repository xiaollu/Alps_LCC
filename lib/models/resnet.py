from tokenize import group
import torch.nn as nn
import torch.utils.model_zoo as model_zoo
from typing import Type, List, Optional

# urls for pretrained models
model_urls = {'resnet50': 'https://download.pytorch.org/models/resnet50-19c8e357.pth'}

def conv3x3(in_planes, out_planes, stride=1, dilation=1):
    ''' 3 x 3 convolution '''
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=dilation, bias=False, dilation=dilation)

def conv1x1(in_planes, out_planes, stride=1):
    ''' 1 x 1 convolution'''
    return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)

# Bottleneck for resnet50
class Bottleneck(nn.Module) :
    expansion = 4
    
    def __init__(self, inplanes, outplanes, stride=1, downsample=None,
                 dilation=1, norm_layer=nn.BatchNorm2d) -> None:
        super().__init__()
        self.conv1 = conv1x1(inplanes, outplanes)
        self.bn1 = norm_layer(outplanes)
        self.conv2 = conv3x3(outplanes, outplanes, stride, dilation)
        self.bn2 = norm_layer(outplanes)
        self.conv3 = conv1x1(outplanes, outplanes * Bottleneck.expansion)
        self.bn3 = norm_layer(outplanes * Bottleneck.expansion)
        
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        identity = x
        
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out
    
class ResNetEncoder(nn.Module):
    def __init__(self, 
                 block = Bottleneck,
                 layers = [3, 4, 6, 3],
                 in_channels = 4,
                 out_channels = [64, 128, 256, 512],
                 norm_layer = nn.BatchNorm2d
                ):
        super(ResNetEncoder, self).__init__
        
        self.in_channels = in_channels 
        self._out_channels = out_channels
        self._norm_layer = norm_layer
        self.inplanes = 64
        self.dilation = 1
        
        # input layer
        # 400, 400, 4 -> 200, 200, 64
        self.conv1 = nn.Conv2d(3, self.inplanes, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = self._norm_layer(self.inplanes)
        self.relu = nn.ReLU(inplace=True)
        # 200, 200, 64 -> 100, 100, 64
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        
        #conv layers
        # 100, 100, 64 -> 100, 100, 256
        self.layer1 = self._make_layer(block, out_channels[0], layers[0])
        # 100, 100, 256 -> 50, 50, 512
        self.layer2 = self._make_layer(block, out_channels[1], layers[1], stride=2)
        # 50, 50, 512 -> 25, 25, 1024
        self.layer3 = self._make_layer(block, out_channels[2], layers[2], stride=2)
        # 25, 25, 1024 -> 13, 13, 2048
        self.layer4 = self._make_layer(block, out_channels[3], layers[3], stride=2)

    @property
    def out_channels(self):
        return [self.in_channels] + self._out_channels
        
        
    def _make_layer(
        self, 
        block: Type[Bottleneck],
        planes: int,
        blocks: int,
        stride: int = 1,
        dilate: bool = False,
    ) -> nn.Sequential:
        norm_layer = self._norm_layer
        downsample = None
        previous_dilation = self.dilation
        if dilate:
            self.dilation *= stride
            stride = 1
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                norm_layer(planes * block.expansion),
            )
            
        layers = []

        layers.append(block(self.inplanes, planes, stride, downsample, dilation=previous_dilation, norm_layer=norm_layer))
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(
                block(
                    self.inplanes,
                    planes, stride, downsample, dilation=self.dilation,
                    norm_layer=norm_layer)
                )
        return nn.Sequential(*layers)
    
    def _foward_impl(self, x): 
        x = self.conv1(x)
        x = self.bn1(x)
        # 200, 200, 64
        feat1 = self.relu(x)
        x = self.maxpool(feat1)
        
        #100, 100, 256
        feat2 = self.layer1(x)
        #50, 50, 512
        feat3 = self.layer2(feat2)
        #25, 25, 1024
        feat4 = self.layer3(feat3)
        #13, 13, 2048
        feat5 = self.layer4(feat4)
        
        return [feat1, feat2, feat3, feat4, feat5]

    def forward(self, x):
        return self._foward_impl(x)
    
def resnet50(pretrained=False, **kwargs):
    model = ResNetEncoder(Bottleneck)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet50']), strict=False)
        
    del model.avgpool
    del model.fc
    return model
        