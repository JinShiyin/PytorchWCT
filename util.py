from __future__ import division
import torch
# from torch.utils.serialization import load_lua
import torchfile
import torchvision.transforms as transforms
import numpy as np
import argparse
import time
import os
from PIL import Image
# from modelsNIPS import decoder1, decoder2, decoder3, decoder4, decoder5
# from modelsNIPS import encoder1, encoder2, encoder3, encoder4, encoder5
from models.encoder_and_decoder.feature_invertor_conv1_1 import feature_invertor_conv1_1
from models.encoder_and_decoder.feature_invertor_conv2_1 import feature_invertor_conv2_1
from models.encoder_and_decoder.feature_invertor_conv3_1 import feature_invertor_conv3_1
from models.encoder_and_decoder.feature_invertor_conv4_1 import feature_invertor_conv4_1
from models.encoder_and_decoder.feature_invertor_conv5_1 import feature_invertor_conv5_1
from models.encoder_and_decoder.vgg_normalised_conv1_1 import vgg_normalised_conv1_1
from models.encoder_and_decoder.vgg_normalised_conv2_1 import vgg_normalised_conv2_1
from models.encoder_and_decoder.vgg_normalised_conv3_1 import vgg_normalised_conv3_1
from models.encoder_and_decoder.vgg_normalised_conv4_1 import vgg_normalised_conv4_1
from models.encoder_and_decoder.vgg_normalised_conv5_1 import vgg_normalised_conv5_1
import torch.nn as nn


class WCT(nn.Module):
    def __init__(self, args):
        super(WCT, self).__init__()
        # load pre-trained network

        self.e1 = vgg_normalised_conv1_1
        self.e1.load_state_dict(torch.load(args.vgg1))
        self.d1 = feature_invertor_conv1_1
        self.d1.load_state_dict(torch.load(args.decoder1))
        self.e2 = vgg_normalised_conv2_1
        self.e2.load_state_dict(torch.load(args.vgg2))
        self.d2 = feature_invertor_conv2_1
        self.d2.load_state_dict(torch.load(args.decoder2))
        self.e3 = vgg_normalised_conv3_1
        self.e3.load_state_dict(torch.load(args.vgg3))
        self.d3 = feature_invertor_conv3_1
        self.d3.load_state_dict(torch.load(args.decoder3))
        self.e4 = vgg_normalised_conv4_1
        self.e4.load_state_dict(torch.load(args.vgg4))
        self.d4 = feature_invertor_conv4_1
        self.d4.load_state_dict(torch.load(args.decoder4))
        self.e5 = vgg_normalised_conv5_1
        self.e5.load_state_dict(torch.load(args.vgg5))
        self.d5 = feature_invertor_conv5_1
        self.d5.load_state_dict(torch.load(args.decoder5))

    def whiten_and_color(self, cF, sF):
        cFSize = cF.size()
        c_mean = torch.mean(cF, 1)  # c x (h x w)
        c_mean = c_mean.unsqueeze(1).expand_as(cF)
        cF = cF - c_mean

        contentConv = torch.mm(cF, cF.t()).div(cFSize[1] - 1) + torch.eye(cFSize[0]).double()
        c_u, c_e, c_v = torch.svd(contentConv, some=False)

        k_c = cFSize[0]
        for i in range(cFSize[0]):
            if c_e[i] < 0.00001:
                k_c = i
                break

        sFSize = sF.size()
        s_mean = torch.mean(sF, 1)
        sF = sF - s_mean.unsqueeze(1).expand_as(sF)
        styleConv = torch.mm(sF, sF.t()).div(sFSize[1] - 1)
        s_u, s_e, s_v = torch.svd(styleConv, some=False)

        k_s = sFSize[0]
        for i in range(sFSize[0]):
            if s_e[i] < 0.00001:
                k_s = i
                break

        c_d = (c_e[0:k_c]).pow(-0.5)
        step1 = torch.mm(c_v[:, 0:k_c], torch.diag(c_d))
        step2 = torch.mm(step1, (c_v[:, 0:k_c].t()))
        whiten_cF = torch.mm(step2, cF)

        s_d = (s_e[0:k_s]).pow(0.5)
        targetFeature = torch.mm(torch.mm(torch.mm(s_v[:, 0:k_s], torch.diag(s_d)), (s_v[:, 0:k_s].t())), whiten_cF)
        targetFeature = targetFeature + s_mean.unsqueeze(1).expand_as(targetFeature)
        return targetFeature

    def transform(self, cF, sF, csF, alpha):
        cF = cF.double()
        sF = sF.double()
        C, W, H = cF.size(0), cF.size(1), cF.size(2)
        _, W1, H1 = sF.size(0), sF.size(1), sF.size(2)
        cFView = cF.view(C, -1)
        sFView = sF.view(C, -1)

        targetFeature = self.whiten_and_color(cFView, sFView)
        targetFeature = targetFeature.view_as(cF)
        ccsF = alpha * targetFeature + (1.0 - alpha) * cF
        ccsF = ccsF.float().unsqueeze(0)
        csF.resize_(ccsF.size()).copy_(ccsF)
        return csF
