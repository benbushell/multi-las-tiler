import time
import sys
import struct
import math
import json


# for i in range(0,10):
#     time.sleep(1)
#     print("test", i)
#     sys.stdout.flush()


defaultJson = '{"quadCompletion": "0", "timeTaken": "0", "quadCompleted": "false", "currX": "0", "currY": "0", "boundaryCount":"0", "boundaries":"0", "boundaryName":"null","boundX":"0", "boundY":"0"}'
jsonData = json.loads(defaultJson)


def getFromBytes(filepath, pos, structCode, bytes):
    # Gets value at pos from with the python struct for the datatype and number of bytes.
    with open(filepath, 'rb', buffering=0) as f:
        f.seek(pos)
        char = f.read(bytes)
        d = struct.unpack(structCode, char)
        return (d[0])


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
        # self.pointRecords = getFromBytes(filePath, 107, 'L', 4) #format < 6
        self.pointRecords = getFromBytes(filePath, 247, 'L', 4)  # format > 5
        self.pointRecordFormat = getFromBytes(filePath, 104, 'B', 1)
        self.pointRecordOffset = getFromBytes(filePath, 96, 'L', 4)
        self.pointRecordLength = getFromBytes(filePath, 105, 'H', 2)
        self.scale = scaleOffset(filePath, 131)
        self.offset = scaleOffset(filePath, 155)
        self.min = minMax(filePath, 187)
        self.max = minMax(filePath, 179)

    def pointRecord(self, pos):
        return PointRecord(pos, self)

    def quadAutoGrid(self, tileSize):

        # Gets min and max tile to nearest whole number.
        minX = (round(self.min.x/tileSize)*tileSize) - tileSize/2
        minY = (round(self.min.y/tileSize)*tileSize) - tileSize/2

        tileArr = []

        i = minX
        count = 0

        # Creates a new Tile object for each coordinate on the grid.
        while i < self.max.x+tileSize:
            j = minY
            while j < self.max.y+tileSize:
                tileArr.append(boundary(i, j, tileSize/2))
                count += 1
                j += tileSize
            i += tileSize

        #print(json.dumps({"tilesize":tileSize, "minX":minX, "minY":minY}))
        return (tileArr)

    def quad(self):
        with open(self.filePath, "rb") as f:

            header = f.read()[:self.pointRecordOffset]

            hd = max(self.max.x - self.min.x, self.max.y - self.min.y)
            # print('Boundary Width : ', hd*2)

            bd = boundary((self.min.x + self.max.x)/2,
                          (self.max.y + self.min.y)/2, hd)
            q = quadtree(bd)

            f.seek(self.pointRecordOffset)
            count = 0
            st = time.time()
            while True:
                # reads one point record at a time based off pointRecordLength.
                b = f.read(self.pointRecordLength)
                if b:
                    # pr = struct.unpack('lllHBBbBH', b) #Format 0
                    pr = struct.unpack(
                        'lllxxxxxxxxxxxxxxxxxxxxxxxx', b)  # Format 7
                    x = (pr[0]*self.scale.x)+self.offset.x
                    y = (pr[1]*self.scale.y)+self.offset.y
                    if (count % 100000 == 0):
                        # print(' ', math.floor((count/self.pointRecords)*100), '%', end="\r")

                        jsonData.update({"quadCompletion": str(math.floor((count/self.pointRecords)*100)),
                                         "timeTaken": str(time.time()-st),
                                         "currX": str(x),
                                         "currY": str(y)})
                        print(json.dumps(jsonData))
                        sys.stdout.flush()

                        # print(count)
                    count += 1
                    q.insert(pt(x, y, b))

                else:
                    break

            et = time.time()

            jsonData.update({"quadCompletion": "100", "timeTaken": str(et-st), "quadCompleted": "true"})
            print(json.dumps(jsonData))
            sys.stdout.flush()


            boundaries = self.quadAutoGrid(25)

            jsonData.update({"boundaries": str(len(boundaries))})
            print(json.dumps(jsonData))
            sys.stdout.flush()

            bcount = 0
            for i in boundaries:
                bcount += 1
                points = []
                q.query(i, points)

                tx = str(i.x)
                ty = str(i.y)

                jsonData.update({"boundaryCount": str(bcount), "boundaryName":i.fileName, "boundX": tx, "boundY":ty, "points":str(len(points))})
                print(json.dumps(jsonData))
                sys.stdout.flush()

                if (len(points) > 100):
                    with open("tiles//"+i.fileName, 'wb') as f_out:
                        f_out.write(header)
                        for p in points:
                            f_out.write(p.raw)

                        f_out.seek(247)  # Point format 7
                        newhex = struct.pack(
                            'QL', len(points), len(points))  # Point Format 7
                        f_out.write(newhex)

                    # jsonData.update({"boundaryCount": str(bcount), "boundaryName": i.fileName, "bounds": {"x":str(i.x), "y":str(i.y)}})
                    # print(json.dumps(jsonData))
                    # sys.stdout.flush()


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


class Tile:
    def __init__(self, x, y, tileSize):
        self.x1 = x
        self.y1 = y
        self.x2 = x + tileSize
        self.y2 = y + tileSize
        self.fileName = 'Tile_X+0000' + str(x) + '_Y+0000' + str(y) + '.las'
        self.prCount = 0

    def __str__(self):
        return f"{self.x},{self.y}"


class boundary:
    def __init__(self, x, y, hd):
        self.x = x
        self.y = y
        self.hd = hd
        self.fileName = 'Tile_X+0000' + \
            str(math.floor(x-hd)) + '_Y+0000' + str(math.floor(y-hd)) + '.las'

    def contains(self, pt):
        if (pt.x >= self.x-self.hd and pt.x <= self.x+self.hd and pt.y >= self.y - self.hd and pt.y <= self.y + self.hd):
            return True
        else:
            return False

    def intersects(self, range):
        # if(range.x - range.hd > self.x + self.hd or range.x + range.hd < self.x - self.hd or range.y - range.hd > self.y + self.hd or range.y + range.hd < self.y - self.hd):
        #     return False
        inter = False

        rangepts = [pt(range.x-range.hd, range.y+range.hd), pt(range.x+range.hd, range.y+range.hd),
                    pt(range.x-range.hd, range.y-range.hd), pt(range.x+range.hd, range.y-range.hd)]
        for p in rangepts:
            if (self.contains(p)):
                inter = True
                break

        selfpts = [pt(self.x-self.hd, self.y+self.hd), pt(self.x+self.hd, self.y+self.hd),
                   pt(self.x-self.hd, self.y-self.hd), pt(self.x+self.hd, self.y-self.hd)]
        for p in selfpts:
            if (range.contains(p)):
                inter = True
                break

        return (inter)

    def __str__(self):
        return (""+str(self.x) + str(self.y) + str(self.hd)+"")


class pt:
    def __init__(self, x, y, raw='na'):
        self.x = x
        self.y = y
        self.raw = raw

    def __str__(self):
        return (str(self.x) + " " + str(self.y))


class quadtree:
    def __init__(self, boundary):
        self.boundary = boundary
        self.points = []
        self.capacity = 10000000
        self.divided = False

    def subdivide(self, pt):
        self.divided = True

        nwb = boundary(self.boundary.x - self.boundary.hd/2,
                       self.boundary.y + self.boundary.hd/2, self.boundary.hd/2)
        self.nw = quadtree(nwb)

        neb = boundary(self.boundary.x + self.boundary.hd/2,
                       self.boundary.y + self.boundary.hd/2, self.boundary.hd/2)
        self.ne = quadtree(neb)

        swb = boundary(self.boundary.x - self.boundary.hd/2,
                       self.boundary.y - self.boundary.hd/2, self.boundary.hd/2)
        self.sw = quadtree(swb)

        seb = boundary(self.boundary.x + self.boundary.hd/2,
                       self.boundary.y - self.boundary.hd/2, self.boundary.hd/2)
        self.se = quadtree(seb)

    def insert(self, pt):
        if (self.boundary.contains(pt) == False):
            return

        else:

            if (len(self.points) < self.capacity):
                self.points.append(pt)

            else:

                if (len(self.points) >= self.capacity and self.divided == False):
                    self.subdivide(pt)

                else:
                    self.nw.insert(pt)
                    self.ne.insert(pt)
                    self.sw.insert(pt)
                    self.se.insert(pt)

    def query(self, range, found):
        if (self.boundary.intersects(range) == False):
            return

        else:
            for p in self.points:
                if (range.contains(p)):
                    found.append(p)

            if (self.divided):
                self.nw.query(range, found)
                self.ne.query(range, found)
                self.sw.query(range, found)
                self.se.query(range, found)


# f = LasFile("C:\\THT Processing\\TBC Projects\\RAD Up 22082022 0.120220823002017-000 to RAD Up 22082022 0.120220823002017-017\\RAD Up 22082022 0.120220823002017-000 to RAD Up 22082022 0.120220823002017-017.las")

# print(f)

# f.quad()
match sys.argv[1]:
    case 'get_file_info':
        # print('Hello to you too!')

        f = LasFile(sys.argv[2])
        print(f)

    case 'begin_tiling':
        # print('See you later')

        f = LasFile(sys.argv[2])
        # print(json.dumps(jsonData))
        f.quad()

    case other:
        print('No match found')
