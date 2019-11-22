from __future__ import print_function
import torch
import torch.nn as nn
import torch.nn.parallel
import torch.utils.data
from model_blocks import GetDecoder, Identity
from template import GetTemplate


class Atlasnet(nn.Module):

    def __init__(self, opt):
        """
        Main Atlasnet module. This network takes an embedding in the form of a latent vector and returns a pointcloud or a mesh
        :param opt: 
        """
        super(Atlasnet, self).__init__()
        self.opt = opt
        self.device = opt.device
        self.nb_pts_in_primitive = opt.number_points / opt.nb_primitives
        if opt.remove_all_batchNorms:
            torch.nn.BatchNorm1d = Identity
            print("Replacing all batchnorms by identities.")

        # Initialize templates
        self.template = [GetTemplate(opt.start_from, device=opt.device) for i in range(0, opt.nb_primitives)]

        # Intialize deformation networks
        self.decoder = nn.ModuleList(
            [GetDecoder(bottleneck_size=opt.bottleneck, input_size=opt.dim_template, decoder_type=opt.decoder) for i in
             range(0, opt.nb_primitives)])

    def forward(self, latent_vector):
        """
        Deform points from self.template using the embedding latent_vector
        :param latent_vector: an opt.bottleneck size vector encoding a 3D shape or an image.
        :return: A deformed pointcloud
        """
        # Sample points in the patches
        input_points = [self.template[i].getRandomPoints() for i in range(self.opt.nb_primitives)]
        input_points = [input_points.expand() for i in range(self.opt.nb_primitives)]

        # Deform each patch
        output_points = torch.cat([self.decoder[i](input_points[i], latent_vector.unsqueeze(2)).unsqueeze(0) for i in
                                   range(0, self.opt.nb_primitives)], dim=0)

        # Deform return the deformed pointcloud
        return output_points.contiguous()  # batch, nb_prim, num_point, 3