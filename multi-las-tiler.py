import json
import sys
import struct
import math
import time

def roundDown(x, base):
    return int(base * math.floor(math.floor(x)/base))


def getFromBytes(filepath, pos, structCode, bytes):
    # Gets value at pos from with the python struct for the datatype and number of bytes.
    with open(filepath, 'rb', buffering=0) as f:
        f.seek(pos)
        char = f.read(bytes)
        d = struct.unpack(structCode, char)
        return (d[0])

def createFileName(x,y):
    return("Tile_X+"+str(x).zfill(8)+"_Y+"+str(y).zfill(8))

class scaleOffset:
    def __init__(self, filePath, pos):
        self.x = getFromBytes(filePath, pos, 'd', 8)
        self.y = getFromBytes(filePath, pos+8, 'd', 8)
        self.z = getFromBytes(filePath, pos+16, 'd', 8)

    def __str__(self):
        return f"{self.x},{self.y},{self.z}"


class minMax:
    def __init__(self, filePath, pos):
        self.x = getFromBytes(filePath, pos, 'd', 8)
        self.y = getFromBytes(filePath, pos+16, 'd', 8)
        self.z = getFromBytes(filePath, pos+32, 'd', 8)

    def __str__(self):
        return f"{self.x},{self.y},{self.z}"


class PointRecord:
    def __init__(self, pos, header):
        with open(header.filePath, 'rb', buffering=0) as f:
            f.seek(pos)
            b = f.read(36)
            self.pr = struct.unpack('lllHBBBBhHdHHH', b)
            self.x = (getFromBytes(header.filePath, pos, 'l', 4)
                      * header.scale.x) + header.offset.x
            self.y = (getFromBytes(header.filePath, pos+4, 'l', 4)
                      * header.scale.y) + header.offset.y
            self.z = (getFromBytes(header.filePath, pos+8, 'l', 4)
                      * header.scale.z) + header.offset.z

    def __str__(self):
        return f"{self.x},{self.y},{self.z}"


class LasFile:
    def __init__(self, filePath):
        self.filePath = filePath
        self.pointRecords = getFromBytes(filePath, 107, 'L', 4) #format < 6
        # self.pointRecords = getFromBytes(filePath, 247, 'L', 4)  # format > 5
        self.pointRecordFormat = getFromBytes(filePath, 104, 'B', 1)
        self.pointRecordOffset = getFromBytes(filePath, 96, 'L', 4)
        self.pointRecordLength = getFromBytes(filePath, 105, 'H', 2)
        self.scale = scaleOffset(filePath, 131)
        self.offset = scaleOffset(filePath, 155)
        self.min = minMax(filePath, 187)
        self.max = minMax(filePath, 179)

    def pointRecord(self, pos):
        return PointRecord(pos, self)

    def tileArr(self, tilesize):

        with open(self.filePath, "rb") as f:

            header = f.read()[:self.pointRecordOffset]

            hd = max(self.max.x - self.min.x, self.max.y - self.min.y)
            # print('Boundary Width : ', hd*2)

            points = {}

            f.seek(self.pointRecordOffset)
            count = 0
            st = time.time()
            while True:
                # reads one point record at a time based off pointRecordLength.
                b = f.read(self.pointRecordLength)
                if b:
                    pr = struct.unpack('lllHBBbBH', b) #Format 0
                    # pr = struct.unpack(
                    #     'lllxxxxxxxxxxxxxxxxxxxxxxxx', b)  # Format 7
                    x = (pr[0]*self.scale.x)+self.offset.x
                    y = (pr[1]*self.scale.y)+self.offset.y
                    count += 1

                    xTile = roundDown(x,25)
                    yTile = roundDown(y,25)
                   
                    filename = createFileName(xTile,yTile)
                    
                    if filename in points.keys(): 
                        points[filename].append(b)
                    else:
                        points[filename]=[b]

                else:
                    break

            et = time.time()


            print('Points sorted in ',round(et-st), ' seconds')
            print('Records : ', count)

            print(points.keys())
            
            st = time.time()

            for name in points:
                if (len(points[name]) > 100):

                    with open("tiles//"+name+'.las', 'wb') as f_out:
                        f_out.write(header)
                        for p in points[name]:
                            f_out.write(p)

                        f_out.seek(107)  # Point format 7
                        newhex = struct.pack(
                            'QL', len(points[name]), len(points[name]))  # Point Format 7
                        f_out.write(newhex)

            et = time.time()
            
            print('Files created in ',round(et-st),' seconds')



    def __str__(self):

        return (json.dumps({'filepath': self.filePath,
                            'pointRecordFormat': self.pointRecordFormat,
                            'pointRecords': self.pointRecords,
                            'pointRecordOffset': self.pointRecordFormat,
                            'pointRecordLength': self.pointRecordLength,
                            'scale': {'x': self.scale.x, 'y': self.scale.y, 'z': self.scale.z},
                            'offset': {'x': self.offset.x, 'y': self.offset.y, 'z': self.offset.z},
                            'min': {'x': self.min.x, 'y': self.min.y, 'z': self.min.z},
                            'max': {'x': self.max.x, 'y': self.max.y, 'z': self.max.z}
                            }))


f = LasFile('.//test_files//A_NB_111124-120241111225516-000#2.las')
print('files running')
f.tileArr(25)
