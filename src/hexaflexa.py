# Hexaflexa makes hexaflexagon printouts
# Copyright (C) 2016 Michael Borinsky
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from math import *
import cairo
import sys
import argparse
from enum import Enum


class FaceType(Enum):
    COMMON = "dur",
    HIDDEN = "moll"


# border = 3/4cm
PAPER_BORDER = .75 * 72.0 / 2.54

PAPER_SIZES = {
    "A4": {"width": 595, "height": 842},
    "LETTER": {"width": 612, "height": 792},
    "LEGAL": {"width": 612, "height": 1008},
    "TABLOID": {"width": 792, "height": 1224}
}


def height_of_triangle(side):
    return sqrt(3)/2 * side


def draw_triangle(
    context,
    side,
    half_side,
    height,
    index,
    face_type
):
    trans = index % 2 == 0

    context.rel_move_to(height, side * (index//2+1))

    if face_type == FaceType.HIDDEN:
        height = -height

    if trans:
        context.rel_line_to(-height, -half_side)
        context.rel_line_to(height, -half_side)
        context.rel_line_to(0, side)
    else:
        context.rel_line_to(-height, half_side)
        context.rel_line_to(0, -side)
        context.rel_line_to(height, half_side)

    context.close_path()


def draw_outline(
    context,
    triangle_side,
    triangle_half_side,
    triangle_height
):
    current_point = context.get_current_point()

    for triangle_index in range(0, 19):
        for face_type in [FaceType.COMMON, FaceType.HIDDEN]:
            draw_triangle(
                context,
                triangle_side,
                triangle_half_side,
                triangle_height,
                triangle_index,
                face_type
            )

            context.set_source_rgb(0.0, 0.0, 0.0)
            context.set_line_width(1)
            context.stroke()

            context.move_to(*current_point)


def transform_to_texture_space(
    context,
    triangle_side,
    triangle_half_side,
    triangle_height,
    face_type,
    ori,
    trans,
    image_width,
    image_height,
    m
):
    translation = {
        FaceType.COMMON: {
            "stone": [(0, 0), (-triangle_height, triangle_half_side)],
            "scissor": [(0, -triangle_side), (-triangle_height, -triangle_half_side)],
            "paper": [(-triangle_height, -triangle_half_side), (0, 0)]
        },
        FaceType.HIDDEN: {
            "stone": [(triangle_height, -triangle_half_side), (triangle_height, -triangle_half_side)],
            "scissor": [(triangle_height, -triangle_half_side), (triangle_height, -triangle_half_side)]
        }
    }

    rotation = {
        FaceType.COMMON:  {
            "stone": [0, 2],
            "scissor": [-4, 6],
            "paper": [-4, 2],
        },
        FaceType.HIDDEN: {
            "stone": [0, -2],
            "scissor": [-4, -6]
        }
    }

    dx, dy = translation[face_type][ori][trans]
    rot = 2*pi/12 * (rotation[face_type][ori][trans] + 2*m)

    ref_size = min(image_width, image_height)
    scale = 2*triangle_side/ref_size

    x, y = context.get_current_point()

    context.translate(x+dx, y+dy)
    context.scale(scale, scale)
    context.rotate(rot)

    context.translate(-.5*image_width, -.5*image_height)


def draw_picture(
    context,
    triangle_side,
    triangle_half_side,
    triangle_height,
    face,
    ori,
    image
):
    current_point = context.get_current_point()
    face_type = FaceType.COMMON if face < 3 else FaceType.HIDDEN

    alpha = 0.4
    image_width, image_height = image.get_width(), image.get_height()
    pat = cairo.SolidPattern(0.0, 0.0, 0.0, alpha)

    for triangle_in_image_index in range(0, 6):
        if face_type == FaceType.COMMON:
            k = 1 + 3*triangle_in_image_index + face
        elif face_type == FaceType.HIDDEN:
            k = triangle_in_image_index % 2 + 2 * \
                (face-3+3*(triangle_in_image_index//2))

        trans = k % 2

        draw_triangle(
            context,
            triangle_side,
            triangle_half_side,
            triangle_height,
            k,
            face_type
        )

        context.save()

        transform_to_texture_space(
            context,
            triangle_side,
            triangle_half_side,
            triangle_height,
            face_type,
            ori,
            trans,
            image_width,
            image_height,
            triangle_in_image_index
        )

        context.clip()
        context.set_source_surface(image)

        if face_type == FaceType.COMMON and ori == "paper":
            context.mask(pat)
        else:
            context.paint()

        context.restore()

        context.move_to(*current_point)


def main():
    parser = argparse.ArgumentParser(
        description='Make a hexaflexagon with a picture printed on each of the six faces.')
    parser.add_argument('pics', type=str, nargs='+',
                        help='Filenames to pictures (only png).')
    parser.add_argument('--output', type=str,
                        help='Output filename (pdf).', default="out.pdf")
    parser.add_argument('--paper', type=str,
                        help='Paper size', default="A4")

    args = parser.parse_args()

    paper_size = PAPER_SIZES.get(args.paper.upper(), None)
    if paper_size == None:
        print("Paper type not understood: '"+args.paper+"'")
        sys.exit(1)

    width = paper_size["width"]
    height = paper_size["height"]

    surface = cairo.PDFSurface(args.output, width, height)
    context = cairo.Context(surface)

    # we need 10 down the spine
    triangle_side = (height - 2*PAPER_BORDER)/10
    triangle_half_side = triangle_side/2
    triangle_height = height_of_triangle(triangle_side)
    horizontal_triangle_count = int(width / (triangle_height*2))

    for i in range(horizontal_triangle_count):
        context.move_to(PAPER_BORDER + i * (2*triangle_height), PAPER_BORDER)

        common_faces = list(zip(range(0, 3), ["scissor"] * 3))
        hidden_faces = list(zip(range(3, 6), ["scissor", "scissor", "stone"]))
        transparent_faces = list(zip(range(0, 3), ["paper"] * 3))

        print(common_faces)
        print(hidden_faces)
        print(transparent_faces)
        print(common_faces + hidden_faces + transparent_faces)

        for path_to_image, (face, ori) in zip(args.pics, common_faces + hidden_faces + transparent_faces):
            image = cairo.ImageSurface.create_from_png(path_to_image)
            draw_picture(
                context,
                triangle_side,
                triangle_half_side,
                triangle_height,
                face,
                ori,
                image
            )

        draw_outline(
            context,
            triangle_side,
            triangle_half_side,
            triangle_height
        )

    surface.show_page()


if __name__ == "__main__":
    main()
