#sample class
from inc_noesis import *
import xml.dom.minidom as xd
import struct


def registerNoesisTypes():
	handle = noesis.register("To LOVE-Ru Darkness: Gravure Chances", ".bum")
	noesis.setHandlerTypeCheck(handle, tlruCheckType)
	noesis.setHandlerLoadModel(handle, tlruLoadModel)
	#noesis.logPopup()
	return 1

def tlruCheckType(data):
	td = NoeBitStream(data)
	return 1

class tlruFile: 
         
	def __init__(self, bs):
		self.texList   = []
		self.vtxList   = []
		self.matList   = []
		self.boneList  = []
		self.partList  = []
		self.usedTex   = {}
		self.bmapDict  = {}
		self.lvl = -1
		self.doc = xd.Document()
		self.parent = []
		self.loadAll(bs)

	def loadAll(self, bs):
		while bs.tell() < bs.dataSize:
			self.readMember(bs)
		#print(self.doc.toxml())
		slides = self.doc.getElementsByTagName("ido")[0]
		self.getChildren(slides)
		#for slide in slides.childNodes:
		#	print(slide.tagName, slide.getAttribute("TRNS"))
		#print(slides.childNodes)
		if len(self.boneList) > 0:
			self.boneList = rapi.multiplyBones(self.boneList)
		self.baseBone = (int(slides.firstChild.getAttribute("PARE")) + 1)
		for a in range(0,len(self.partList)):
			bs.seek(self.partList[a][0], NOESEEK_ABS)
			self.readPart(bs,self.partList[a][0] + self.partList[a][1] - 8)
	
	def getChildren(self,elem):
		for slide in elem.childNodes:
			#print(slide.tagName, slide.getAttribute("TRNS"))
			if slide.getAttribute("ROTQ"):
				matrix = NoeQuat(eval(slide.getAttribute("ROTQ"))).toMat43().inverse()
			else:
				matrix = NoeQuat((0,0,0,1)).toMat43()
			if slide.getAttribute("TRNS"):
				matrix[3] = eval(slide.getAttribute("TRNS"))
			else:
				matrix[3] = eval(slide.parentNode.getAttribute("TRNS"))
			#print(matrix)
			newBone = NoeBone(len(self.boneList), slide.tagName, matrix, parentName = slide.parentNode.tagName, parentIndex = None)
			self.boneList.append(newBone)
			if slide.hasChildNodes():
				self.getChildren(slide)

	
	def readMember(self, bs):
		base = bs.tell()
		tag = bs.readBytes(4).decode("ASCII").rstrip("\0")
		size = bs.readUInt()
		#print(tag)
		if tag == ".BUM":
			pass
		elif tag == "MODL":
			pass
		elif tag == "PART":
			self.partList.append([bs.tell(),size])
		elif tag == "MATR":
			self.readMatr(bs,base + size)
		elif tag == "MATS":
			self.readMats(bs,base + size)
		elif tag == "NODE":
			self.lvl += 1
			nodeDic = self.readNode(bs,base + size)
			node = self.doc.createElement(nodeDic["NAME"])
			if "TRNS" in nodeDic:
				node.setAttribute("TRNS",str(nodeDic["TRNS"]))
			if "BLEB" in nodeDic:
				node.setAttribute("BLEB",str(nodeDic["BLEB"]))
			if "ROTQ" in nodeDic:
				node.setAttribute("ROTQ",str(nodeDic["ROTQ"]))
			if "PARE" in nodeDic:
				node.setAttribute("PARE",str(nodeDic["PARE"]))
			#if "BLEB" in nodeDic:
			#	node.setAttribute("BLEB",str(nodeDic["BLEB"]))
			self.parent.append(node)
			if self.lvl != 0:
				self.parent[nodeDic["PARE"]].appendChild(node)
			else:
				self.doc.appendChild(node)
		elif tag == "NAME":
			name = bs.readBytes(size - 8).decode("ASCII").rstrip("\0")
			#print(self.lvl, name)
		else:
			#print(tag)
			bs.seek(base + size, NOESEEK_ABS)

	def readPart(self, bs, end):
		SMAT = []
		BLES = []
		DRWA = []
		ARAY = []
		ARAS = []
		while bs.tell() < end:
			base = bs.tell()
			tag = bs.readBytes(4).decode("ASCII").rstrip("\0")
			size = bs.readUInt()
			if tag == "NAME":
				name = bs.readBytes(size - 8).decode("ASCII").rstrip("\0")
				rapi.rpgSetName(name)
				boneMap = []
				for a in range(0,len(self.bmapDict[name])):
					boneMap.append(self.bmapDict[name][a] - self.baseBone)
					if boneMap[a] < 0:
						boneMap[a] = 0
				rapi.rpgSetBoneMap(boneMap)
				#print(name)
				#print(boneMap)
			elif tag == "BBOX":
				bbox = bs.read("6f")
			elif tag == "SMAT":
				SMAT.append(bs.read("I")[0])
			elif tag == "BLES":
				bcount = bs.read("I")[0]
				BLES.append(bs.read(8 * "I"))
				bs.seek(base + size, NOESEEK_ABS)
			elif tag == "DRWA":
				info = bs.read("2BH")
				data = bs.readBytes(size - 12)
				DRWA.append((info,data))
			elif tag == "ARAY":
				info = bs.read("2H")
				stride = (size - 12) // info[1]
				data = bs.readBytes(size - 12)
				ARAY.append((info,stride,data))
			elif tag == "ARAS":
				info = bs.read("2h")
				data = bs.readBytes(size - 12)
				if info[0] == -1:
					stride = 0
				else:
					stride = (size - 12) // info[1]
				ARAS.append((info,stride,data))
			elif tag == "MESH":
				pass
			else:
				bs.seek(base + size, NOESEEK_ABS)
		#print(SMAT)
		#print(BLES)
		#print(DRWA)
		#print(ARAY)
		#print(ARAS)
		for a in range(0,len(DRWA)):
			#print(DRWA[a][0])
			#print(BLES[a])
			rapi.rpgSetMaterial(self.matList[SMAT[a]].name)
			#print(ARAY[DRWA[a][0][1]][1])
			#print(ARAS[DRWA[a][0][1]][1])
			idxBuff = struct.pack("<" + 'H'*len(BLES[a]), *BLES[a]) * (len(ARAY[DRWA[a][0][1]][2]) // ARAY[DRWA[a][0][1]][1])
			if ARAY[DRWA[a][0][1]][1] == 28:
				rapi.rpgBindPositionBufferOfs(ARAY[DRWA[a][0][1]][2], noesis.RPGEODATA_FLOAT, ARAY[DRWA[a][0][1]][1], 0)
				rapi.rpgBindUV1BufferOfs(ARAY[DRWA[a][0][1]][2], noesis.RPGEODATA_FLOAT, ARAY[DRWA[a][0][1]][1], 12)
				rapi.rpgBindBoneWeightBufferOfs(ARAY[DRWA[a][0][1]][2], noesis.RPGEODATA_UBYTE, ARAY[DRWA[a][0][1]][1], 20, 8)
				rapi.rpgBindBoneIndexBufferOfs(idxBuff, noesis.RPGEODATA_USHORT, 16, 0, 8)
				rapi.rpgCommitTriangles(DRWA[a][1], noesis.RPGEODATA_USHORT, DRWA[a][0][2], noesis.RPGEO_TRIANGLE, 1)
			elif ARAY[DRWA[a][0][1]][1] == 32:
				rapi.rpgBindPositionBufferOfs(ARAY[DRWA[a][0][1]][2], noesis.RPGEODATA_FLOAT, ARAY[DRWA[a][0][1]][1], 0)
				rapi.rpgBindNormalBufferOfs(ARAY[DRWA[a][0][1]][2], noesis.RPGEODATA_FLOAT, ARAY[DRWA[a][0][1]][1], 12)
				#rapi.rpgBindBoneWeightBufferOfs(ARAY[DRWA[a][0][1]][2], noesis.RPGEODATA_BYTE, ARAY[DRWA[a][0][1]][1], 24, 8)
				#rapi.rpgBindBoneIndexBufferOfs(idxBuff, noesis.RPGEODATA_USHORT, 16, 0, 8)
				#rapi.rpgCommitTriangles(DRWA[a][1], noesis.RPGEODATA_USHORT, DRWA[a][0][2], noesis.RPGEO_TRIANGLE, 1)
			rapi.rpgClearBufferBinds()
			
			
	def readNode(self, bs, end):
		node = {}
		while bs.tell() < end:
			base = bs.tell()
			tag = bs.readBytes(4).decode("ASCII").rstrip("\0")
			size = bs.readUInt()
			if tag == "NAME":
				name = bs.readBytes(size - 8).decode("ASCII").rstrip("\0")
				node["NAME"] = name
			elif tag == "TRNS":
				pos = bs.read("3f")
				node["TRNS"] = pos
			elif tag == "ROTQ":
				rot = bs.read("4f")
				node["ROTQ"] = rot
				#print(rot)
			elif tag == "BBOX":
				bbox = bs.read("6f")
				node["BBOX"] = bbox
			elif tag == "PARE":
				par = bs.read("i")[0]
				node["PARE"] = par
			elif tag == "BLEB":
				bl = bs.read("i")[0]
				bmap = bs.read(bl * "H")
				#print(node["NAME"])
				#print(bmap)
				node["BLEB"] = str(bmap)
				self.bmapDict[node["NAME"]] = bmap
				#print(self.bmapDict[node["NAME"]])
			else:
				node[tag] = ""
			bs.seek(base + size, NOESEEK_ABS)
		return(node)
			

	def readMatr(self, bs, end):
		material = NoeMaterial("", "")
		while bs.tell() < end:
			base = bs.tell()
			tag = bs.readBytes(4).decode("ASCII").rstrip("\0")
			size = bs.readUInt()
			if tag == "NAME":
				name = bs.readBytes(size - 8).decode("ASCII").rstrip("\0")
				material.name = name
			elif tag == "EMIS":
				emis = bs.read("4f")
				material.setDiffuseColor(emis)
			bs.seek(base + size, NOESEEK_ABS)
		self.matList.append(material)
		
	def readMats(self, bs, end):
		type = bs.read("2H")
		tag,size = bs.read("2I")
		materialName = bs.readBytes(size - 8).decode("ASCII").rstrip("\0")
		tag,size = bs.read("2I")
		shaderName = bs.readBytes(size - 8).decode("ASCII").rstrip("\0")
		#print(materialName,shaderName)
		for a in range(0,len(self.matList)):
			if self.matList[a].name == materialName:
				material = self.matList[a]
		while bs.tell() < end:
			base = bs.tell()
			tag = bs.readBytes(4).decode("ASCII").rstrip("\0")
			size = bs.readUInt()
			if tag == "SFPR":
				fcount = bs.read("i")[0]
				floats = bs.read(fcount * "f")
				name = bs.readBytes(size - (12 + (4 * fcount))).decode("ASCII").rstrip("\0")
				#print(name,floats)
			elif tag == "SAMP":
				self.readSamp(bs,base + size,material)
			else:
				pass
				#print(tag)
			bs.seek(base + size, NOESEEK_ABS)

	def readSamp(self, bs, end, mat):
		tag,size = bs.read("2I")
		texSlot = bs.readBytes(size - 8).decode("ASCII").rstrip("\0")
		tag,size = bs.read("2I")
		texName = bs.readBytes(size - 8).decode("ASCII").rstrip("\0")
		secondPassMat = NoeMaterial(mat.name + "_ambient", texName)
		secondPassMat.setFlags(noesis.NMATFLAG_TWOSIDED, 1)
		secondPassMat.setDiffuseColor( (3.0, 3.0, 3.0, 1.0) )
		mat.setNextPass(secondPassMat)
		if texName in self.usedTex:
			pass
		else:
			if( rapi.checkFileExists( rapi.getDirForFilePath( rapi.getLastCheckedName() ) + texName + ".png" ) ):
				texFile = rapi.loadIntoByteArray( rapi.getDirForFilePath( rapi.getLastCheckedName() ) + texName + ".png" )
				tex = rapi.loadTexByHandler(texFile,".png")
				texData = rapi.imageEncodeRaw(tex.pixelData, tex.width, tex.height, "r8g8b8m8")
				tex = NoeTexture(texName, tex.width, tex.height, texData, noesis.NOESISTEX_RGBA32)
				self.texList.append(tex)
				self.usedTex[texName] = texName
		unk = bs.read("i")[0]
		#print(texSlot,texName,unk)
		mat.setTexture(texName)
		while bs.tell() < end:
			base = bs.tell()
			tag = bs.readBytes(4).decode("ASCII").rstrip("\0")
			size = bs.readUInt()
			bs.seek(base + size, NOESEEK_ABS)


def tlruLoadModel(data, mdlList):
	ctx = rapi.rpgCreateContext()
	tlru = tlruFile(NoeBitStream(data))
	try:
		mdl = rapi.rpgConstructModel()
	except:
		mdl = NoeModel()
	mdl.setModelMaterials(NoeModelMaterials(tlru.texList, tlru.matList))
	mdlList.append(mdl); mdl.setBones(tlru.boneList)	
	return 1

