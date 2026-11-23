#!/usr/bin/env python3
"""Original, schematic VMC850: millimetres, twelve-pocket pneumatic ATC."""
import math
import time
import hal
from OpenGL.GL import glPushMatrix, glRotatef
from vismach import Box, CylinderZ, CylinderY, Collection, Color, HalTranslate, HalRotate, Translate, Capture, main

c = hal.component("vmcgui")
for name in ("X", "Y", "Z", "carousel", "magazine", "door", "drawbar", "pickup", "spindle-tool", "z-clear", "spindle-angle", "orient-target", "orient-ok"):
    c.newpin(name, hal.HAL_FLOAT, hal.HAL_IN)
c.ready()

def paint(rgb, parts):
    return Color([*rgb, 1], parts)

class ToolVisibility(Collection):
    def __init__(self, parts, pocket=0):
        super().__init__(parts)
        self.pocket = pocket

    def traverse(self):
        selected = int(c["spindle-tool"])
        if (self.pocket == 0 and selected > 0) or (self.pocket > 0 and selected != self.pocket):
            super().traverse()

class OrientLamp(Collection):
    def __init__(self, parts, on):
        super().__init__(parts)
        self.on = on

    def traverse(self):
        if bool(c["orient-ok"]) == self.on:
            super().traverse()

class AnimatedCarousel(HalRotate):
    def __init__(self, parts):
        super().__init__(parts,c,"carousel",-30,0,0,1)
        self.position = 0.0
        self.last = time.monotonic()

    def apply(self):
        now = time.monotonic()
        dt = min(now-self.last, .1)
        self.last = now
        delta = (c["carousel"]-self.position+6) % 12-6
        self.position += max(-dt*3, min(dt*3,delta))
        glPushMatrix()
        glRotatef(-30*self.position,0,0,1)

base = paint((.30,.34,.38), [Box(-850,-650,0,850,650,300)])
column = paint((.72,.75,.78), [Box(-350,300,300,350,650,2300)])
saddle = paint((.18,.40,.46), [Box(-650,-350,320,650,250,460)])
table = paint((.65,.68,.72), [Box(-500,-250,470,500,250,540)])
slots = paint((.15,.17,.19), [Box(-495,y,540,495,y+8,543) for y in (-180,-90,0,90,180)])
work = Capture()
table = HalTranslate([table, slots, work], c, "X", 1,0,0)
table = HalTranslate([saddle, table], c, "Y", 0,1,0)
head = paint((.83,.85,.88), [Box(-220,-80,1250,220,450,1650)])
spindle = paint((.20,.23,.26), [CylinderZ(1150,65,1320,65)])
# Two drive dogs and a unique orange witness mark rotate with the spindle.
nose = paint((.55,.58,.62),[CylinderZ(1150,82,1180,82)])
dogs = paint((.92,.74,.20),[Box(36,-12,1132,64,12,1155),Box(-64,-12,1132,-36,12,1155)])
witness = paint((1,.45,.04),[Box(65,-10,1152,85,10,1183)])
rotor = HalRotate([nose,dogs,witness],c,"spindle-angle",1,0,0,1)
# Red stationary reference points to configured M19 target (180 degrees).
reference = paint((1,.10,.10),[Box(88,-7,1150,120,7,1185)])
reference = HalRotate([reference],c,"orient-target",1,0,0,1)
bracket = paint((.3,.35,.4),[Box(-135,-40,1170,-105,40,1255)])
lamp_shape = [CylinderY(-48,14,-41,14)]
lamp = Translate([
    OrientLamp([paint((.1,1,.2),lamp_shape)],True),
    OrientLamp([paint((.65,.1,.08),lamp_shape)],False),
],-122,0,1220)
drawbar = paint((.95,.52,.12), [CylinderZ(1630,24,1740,24)])
drawbar = HalTranslate([drawbar],c,"drawbar",0,0,35)
tooltip = Capture()
tool = paint((.85,.66,.15), [CylinderZ(1050,14,1150,30)])
tool = ToolVisibility([tool])
tool = Collection([tool,tooltip])
head = HalTranslate([head,spindle,rotor,reference,bracket,lamp,drawbar,tool],c,"z-clear",0,0,200)
head = HalTranslate([head],c,"Z",0,0,1)

# Horizontal umbrella carousel. Pocket centres are on a 250 mm radius.
# Retracted centre X=-800; 550 mm slide puts pocket 1 at spindle X=0.
disc = paint((.18,.40,.68), [CylinderZ(1080,190,1092,190)])
hub = paint((.32,.36,.40), [CylinderZ(1040,65,1120,65)])
holders=[]
for index in range(12):
    a=2*math.pi*index/12
    x,y=250*math.cos(a),250*math.sin(a)
    # Taper points up into the spindle; cutter points down toward the table.
    holder=paint((.88,.67,.18),[
        CylinderZ(1100,28,1150,14),
        CylinderZ(1090,35,1100,35),
        CylinderZ(1040,18,1090,18),
    ])
    cutter=paint((.68,.70,.72),[CylinderZ(1000,9,1040,9)])
    fork=paint((.38,.43,.48),[Box(180,-12,1080,252,12,1090)])
    from vismach import Rotate
    holders.append(Rotate([fork],index*30,0,0,1))
    holders.append(ToolVisibility([Translate([holder,cutter],x,y,0)],index+1))
# An asymmetric red index marker makes rotation visible even with all tools loaded.
marker = paint((.95,.12,.10),[Box(135,-18,1093,185,18,1103)])
disc = AnimatedCarousel([disc,hub,marker,*holders])
disc = Translate([disc],-800,0,0)
support=paint((.40,.45,.50),[Box(-900,55,920,-730,170,1050)])
cylinder=paint((.7,.72,.74),[Box(-1120,100,940,-860,150,1000)])
magazine=HalTranslate([disc,support],c,"magazine",550,0,0)
door=paint((.25,.68,.75),[Box(-400,-310,920,-370,300,1220)])
door=HalTranslate([door],c,"door",0,0,650)
frame=paint((.45,.50,.54),[Box(-1100,220,300,-1060,260,1900),Box(-1100,220,1860,-320,260,1900)])
floor=paint((.17,.19,.22),[Box(-1300,-850,-30,1100,850,0)])
model=Collection([floor,base,column,table,head,magazine,cylinder,door,frame])
main(model,tooltip,work,1900,lat=-65,lon=220)
