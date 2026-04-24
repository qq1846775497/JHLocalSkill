import P4
import sys
import os
import traceback
import requests
import json
#from desWorker import *
#CONFLICT_SERVER_URL = "http://127.0.0.1:8090/"
CONFLICT_SERVER_URL = "http://10.1.60.6:8095/api/branch_status"

class mergeWorker():
    def __init__(self, p4, sourceStream, targetStream, file, acceptTarget, change, operator):
        self.p4 = p4
        self.sourceStream = "//NXX_Stream/" + sourceStream
        self.targetStream = "//NXX_Stream/" + targetStream
        self.acceptTarget = acceptTarget
        self.file = file
        self.change = str(change)
        self.operator = operator

    def switchStream(self):
        try:
            self.p4.run('client', "-f", '-s', '-S', self.targetStream)
            return True
        except Exception as e:
            print(e)
            return False

    def reverFiles(self):
        try:
            result = self.p4.run('revert', '//...')
            print(result)
        except Exception as e:
            print(e)

    def getDes(self, change, fromStream, operator, targetStr):
        res = oP4.run("describe", change)
        des = res[0]
        sDescOrg = des["desc"]
        sUser = des["user"]
        sDesc = des["desc"]
        sFromStream = fromStream
        schange = change

        if sDescOrg.startswith("[原始提交]"):
            userIndex = sDescOrg.find("user:")
            descriptionIndex = sDescOrg.find("description:")
            streamIndex = sDescOrg.find("stream:")
            changeIndex = sDescOrg.find("change:")
            if userIndex != -1 and descriptionIndex != -1:
                sUser = sDescOrg[userIndex + 6:descriptionIndex].replace("\n", "")
            if descriptionIndex != -1 and streamIndex != -1:
                sDesc = sDescOrg[descriptionIndex + 13: streamIndex].replace("\n", "")
            if streamIndex != -1 and changeIndex != -1:
                sFromStream = sDescOrg[streamIndex + 8:changeIndex].replace("\n", "")
            if changeIndex != -1:
                schange = sDescOrg[changeIndex + 8:].replace("\n", "")
        else:
            try:
                jsondata = json.loads(sDescOrg)
                sUser = jsondata.get("user", sUser)
                sDesc = jsondata.get("des", sDesc)
                sFromStream = jsondata.get("stream", sFromStream)
                schange = jsondata.get("change", schange)
            except:
                pass

#        des = "{}\nuser: {}\ndescription: {}\nstream: {}\nchange: {}\n{}".format("[原始提交]", sUser, sDesc,
#                                                                                 sFromStream, schange, targetStr)
        if (len(operator) > 0 and operator == "None"):
            operator = None
        #des = desWorker.genDes(sDesc, sUser, schange, sFromStream, operator, targetStr)
        return des

    def try_2_submit(self):
        selectStream = ""
        if self.acceptTarget:
            selectStream = "T"
        else:
            selectStream = "S"
        #msg = "{0}->{1}-{2}".format(self.getShortStream(self.sourceStream), self.getShortStream(self.targetStream), selectStream)
        msg = self.getDes(self.change, self.sourceStream, self.operator, selectStream)
        try:
            self.p4.run('submit', '-d', msg)
        except Exception as e:
            print(e)

    def getShortStream(self, stream):
        index = stream.find("NXX_Stream/")
        if index != -1:
            return stream[index + 10:]
        return stream

    def freshConflict(self, source_file, target_file):
        try:
            interchanges = self.p4.run("interchanges", source_file, target_file)
            print(interchanges)
        except Exception:
            trace = traceback.format_exc()
            print(trace)
            if "no files(s) integrated" in trace:
                print("no files(s) integrated")
            if "all revision(s) already integrated" in trace:
                data = {
                    "target_file": target_file,
                    "changelist": self.change
                }
                url = CONFLICT_SERVER_URL + "/resolve_conflict"
                r = requests.post(url, json=data)
                if 200 == r.status_code:
                    # 修改成功
                    print("resolved")
                else:
                    print("API Error")

    def getSourceFile(self):
        return self.file.replace(self.targetStream, self.sourceStream)

    def run(self):
        self.reverFiles()

        if not self.switchStream():
            print("switch to {0} failed!!!".format(self.targetStream))
            return False


        try:
            result = self.p4.run("sync", "-f", self.file+"#head")
            print(result)
        except Exception as e:
            print(e)

        try:
            result = self.p4.run("merge", "-F", "-S", self.targetStream, "-P", self.sourceStream, "-r", self.file + "@" + self.change)
            #+ "," + "@ " + self.change)
            print(result)
        except Exception as e:
            print(e)

        try:
            if self.acceptTarget:
                result = self.p4.run("resolve", "-ay", self.file)
            else:
                result = self.p4.run("resolve", "-at", self.file)
            print(result)
        except Exception as e:
            print (e)

        self.try_2_submit()

        self.reverFiles()

        self.freshConflict(self.getSourceFile(), self.file)






oP4 = P4.P4()
oP4.user = os.environ.get("P4_USER")
oP4.password = os.environ.get("P4_PASSWD")
oP4.client = os.environ.get("P4_CLIENT")
oP4.port = os.environ.get("P4_PORT")
oP4.charset = "utf8"
oP4.api_level = 85
oP4.connect()

sourceStream = sys.argv[1]
targetStream = sys.argv[2]
file = sys.argv[3]
change = sys.argv[4]
acceptTarget = sys.argv[5]
operator = sys.argv[6]
worker = mergeWorker(oP4, sourceStream, targetStream, file, acceptTarget == "true" or acceptTarget == "True", change, operator)
worker.run()