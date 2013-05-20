"""
Render t-SNE text labels.
Requires PIL (Python Imaging Library) and ImageMagick "convert" command.
"""

import sys
import Image, ImageFont, ImageDraw, ImageChops, string

import random
random.seed(0)

import os.path

import tempfile

label_to_color = {}
label_to_outline= {}
for l in range(-1,10000):
    r = int(256*random.random()*0.75)
    g = int(256*random.random()*0.75)
    b = int(256*random.random()*0.75)
    label_to_color[l] = (r, g, b)
    r = int(256*random.random()*0.75)
    g = int(256*random.random()*0.75)
    b = int(256*random.random()*0.75)
    label_to_outline[l] = (r, g, b)

#def render(points, filename, width=3000, height=1800, margin=0.05, transparency=0.5, radius=3):
def render(labels, points, filename, width=6000, height=3600, margin=0.05, transparency=0.1, radius=8):
    """
    Render t-SNE text points to an image file.
    points is a list of tuples of the form (x, y).
    filename should be a .png, typically.
    margin is the amount of extra whitespace added at the edges.
    transparency is the amount of transparency in the text.
    @warning: Make sure you open the PNG in Gimp, or something that supports alpha channels. Otherwise, it will just look completely black.
    """
    W = width
    H = height

    #im = Image.new("L", (W, H), 255)
    im = Image.new("RGBA", (W, H), (0,0,0))

    #draw = ImageDraw.Draw(im)
    
    minx = 0
    maxx = 0
    miny = 0
    maxy = 0
    for (x, y) in points:
        if minx > x: minx = x
        if maxx < x: maxx = x
        if miny > y: miny = y
        if maxy < y: maxy = y

    dx = maxx - minx
    dy = maxy - miny
    assert dx > 0
    assert dy > 0
    minx -= dx * margin
    miny -= dy * margin
    maxx += dx * margin
    maxy += dy * margin


    alpha = Image.new("RGBA", im.size, "white")
    draw = ImageDraw.Draw(alpha)

    for (idx, (l, pt)) in enumerate(zip(labels, points)):
        (x, y) = pt
        x = 1. * (x - minx) / (maxx - minx) * W
        y = 1. * (y - miny) / (maxy - miny) * H

        pos = (x, y)
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=label_to_color[l], outline=label_to_outline[l])
            
    # Add the alpha channel to the image, and save it out.
    #im.putalpha(alpha)
    im = alpha

    tmpf = tempfile.NamedTemporaryFile(suffix=".png")

    #im.save("transtext.png", "PNG")
    print >> sys.stderr, "Rendering alpha image to file", tmpf.name
    im.save(tmpf.name)

    cmd = "convert %s -background white -flatten %s" % (tmpf.name, filename)
    print >> sys.stderr, "Flattening image", tmpf.name, "to", filename, "using command:", cmd
    os.system(cmd)
