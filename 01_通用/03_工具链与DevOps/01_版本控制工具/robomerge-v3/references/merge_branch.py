# -*- coding:utf-8 -*-
import P4
import os
import re
import argparse
import io
import sys
import requests
import json
#from desWorker import *
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sConflictPage = 'http://10.1.60.6:8995/branch_status/branch_conflict'
sMergeUrl = 'https://km.mihoyo.com/articleBase/416/161085'

def merge_branch(sSrcBranch, sDestBranch, sChangelist, sAdminUser, lRobotAccounts, lRevertPath, bFull):
    try:
        oP4.run("switch", "-Rn", sDestBranch)
        oP4.run("sync", "//NXX_Stream/" + sDestBranch + "/...#head")
        cleanUp(oP4)
        # generate a change
        dChange = generateChange(sSrcBranch, sDestBranch, sChangelist)
        if not dChange:
            sMsg = "[AutoMerge]Exception when generate changes!\nStream <{}> To <{}>".format(sSrcBranch, sDestBranch)
            SendMsgToAdminGroup(sMsg)
            oP4.disconnect()
            return 1
        elif not dChange['Desc']:
            oP4.disconnect()
            return 0

        # try to merge
        sResult = tryToMerge(oP4, sSrcBranch, sDestBranch, dChange, bFull, sAdminUser, lRobotAccounts, sChangelist)
        # sResult = Failed, found locked file during merge
        # sResult = NoNeed, whole changelist already integrated
        if sResult == "NoNeed":
            cleanUp(oP4)
            oP4.disconnect()
            return 0

        # revert exclude path
        if len(lRevertPath) > 0 and lRevertPath[0] != '':
            sResult = revertExclude(oP4, lRevertPath)
            if sResult == "AllRevert":
                sMsg = "[Info] All Files reverted when copy from <{}> to <{}>.".format(sSrcBranch, sDestBranch)
                print(sMsg)
                cleanUp(oP4)
                oP4.disconnect()
                return 0
            elif sResult == "RevertError":
                sMsg = "[AutoMerge]Exception when revert file in exclude path!\nStream <{}> To <{}>".format(
                    sSrcBranch, sDestBranch)
                SendMsgToAdminGroup(sMsg)
                cleanUp(oP4)
                oP4.disconnect()
                return 103

        # p4 resolve
        bResult = tryToResolve(oP4, dChange, sAdminUser)
        if not bResult:
            sMsg = "[AutoMerge]Exception when resolve file automatically (no merging)!\nStream <{}> To <{}>".format(
                sSrcBranch, sDestBranch)
            SendMsgToAdminGroup(sMsg)
            cleanUp(oP4)
            oP4.disconnect()
            return 102

        handleConflict(oP4, dChange, sAdminUser, lRobotAccounts, sSrcBranch, sDestBranch)

        # try to submit
        bResult = tryToSubmit(oP4, dChange, sAdminUser, lRobotAccounts, sSrcBranch, sDestBranch)
        cleanUp(oP4)
        oP4.disconnect()
        if bResult:
            return 0
        else:
            return 1
    except Exception as e:
        print("[Error] Something Wrong. Run the merge commands manually to solve the problem")
        print(e)
        sMsg = "[AutoMerge]Uncaught exceptions!\nStream <{}> To <{}>".format(sSrcBranch, sDestBranch)
        SendMsgToAdminGroup(sMsg)
        cleanUp(oP4)
        oP4.disconnect()
        raise

# Generate a Pending Change in default pending changelist by the original changelist.
def generateChange(sSrcBranch, sDestBranch, sChangelist):
    lResult = oP4.run('describe', '-s', sChangelist)
    sUser = lResult[0]['user']
    sDescOrg = lResult[0]['desc']
    sDesc = sDescOrg
    sFromStream = sSrcBranch
    schange = sChangelist
    try:
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

        #sDesc = "{}\nuser: {}\ndescription: {}\nstream: {}\nchange: {}".format("[原始提交]", sUser, sDesc, sFromStream, schange)
        #sDesc = desWorker.genDes("test", "ruilin.ye", "123456", "main")
        #sDesc = desWorker.genDes(sDesc, sUser, schange, sFromStream)
        return {'User': sUser, 'Desc': sDesc, 'FromStream': sFromStream}
    except P4.P4Exception as p4e:
        print("[Error]" + str(p4e))
        return None

# Try to Merge the Change
def tryToMerge(oP4, sSrcBranch, sDestBranch, dChange, bFull, sAdminUser, lRobotAccounts, sChangelist):
    result = "Success"
    sPattern = r'(.*)\s\-\scan\'t\sintegrate\sexclusive\sfile\salready\sopened'
    oMatch = re.compile(sPattern)
    cmdParams = ''
    if bFull == "true":
        print("[Info] Full Merge")
        cmdParams = ["integrate", "//NXX_Stream/" + sSrcBranch + "/...@" + sChangelist, "//NXX_Stream/" + sDestBranch + "/..."]
    elif bFull == "false":
        cmdParams = ["integrate", "//NXX_Stream/" + sSrcBranch + "/...@" + sChangelist + ",@" + sChangelist,
                     "//NXX_Stream/" + sDestBranch + "/..."]
    try:
        print("[Info Start Mergeing]")
        oP4.run(cmdParams)
        exclusives = []
        for dResult in oP4.warnings:
            if isinstance(dResult, str) and oMatch.match(dResult):
                exclusive_file = oMatch.match(dResult).groups()[0]
                print(exclusive_file)
                sWorkspace = oP4.run('fstat', exclusive_file)[0]['otherOpen'][0]
                print(''.join(['Exclusive file: ', exclusive_file, ' is locked in workspace: ', sWorkspace]))
                handleLockedFile(exclusive_file, sSrcBranch, sDestBranch, sChangelist, True)
                exclusives.append([exclusive_file, GetDestUser(exclusive_file, True)])
                result = "Failed"
        if len(exclusives) > 0:
            sendMsgToLockedUser(exclusives, sSrcBranch, sDestBranch, sChangelist)
            sendMsgToLockerGroup(exclusives, sSrcBranch, sDestBranch, sChangelist)
    except P4.P4Exception as p4e:
        print(p4e)
        if "all revision(s) already integrated" in str(p4e):
            print("[Info] No Need to merge from <{}> to <{}>".format(sSrcBranch, sDestBranch))
            print("[Info] nChangelist: " + sChangelist)
            print("[Info] nDescription: " + dChange["Desc"].split('description: ')[-1])
            result = "NoNeed"
    return result

# Try to Resolve files automatically (no merging) in the Change
def tryToResolve(oP4, dChange, sAdminUser):
    try:
        # lBranchFiles = []
        cmdParams = ["resolve", "-am", "-c", "default"]
        oP4.run(cmdParams)
        # lResult = oP4.run("resolve", "-n")
        # for dEle in lResult:
        #     if dEle['resolveType'] == 'branch' or dEle['resolveType'] == 'delete':
        #         lBranchFiles.append(dEle['clientFile'])
        # oP4.run("resolve", "-at", lBranchFiles)
        return True
    # resolve error, not a conflict, need admin to solve problem
    except P4.P4Exception as p4e:
        if 'No file(s) to resolve.' in str(p4e):
            print("[Warning] " + str(p4e))
            return True
        print("[Error] " + str(p4e))
        sSendDestBranch = sDestBranch
        sMsg = "从<{}>合并到<{}>出现问题，需要手动处理\n\nChangelist：{}。\nDescription：{}".format(
            sSrcBranch, sSendDestBranch, sChangelist, dChange["Desc"].split('description: ')[-1])
        print("[Info] Sending Message to Admin")
        print("[Info] Msg: " + sMsg)
        print("[Info] User: " + sAdminUser)
        SendMsgToAdminGroup(sMsg)
        return False

# Revert Files in Exclude Path in the Change
def revertExclude(oP4, lRevertPath):
    try:
        # for e in lRevertPath:
        print("[Debug] Start revert files in exclude path. Path is: ")
        print("=========lRevertPath==========")
        print(lRevertPath)
        print("=========Finish==========")
        cmdParams = ["revert", "-w", lRevertPath]
        oP4.run(cmdParams)
    except P4.P4Exception as p4e:
        if "Warnings during command execution" in str(p4e):
            cmdParams = ["opened"]
            result = oP4.run(cmdParams)
            if len(result) == 0:
                print("[Info] All Files reverted. No files to submit.")
                return "AllRevert"
            print("[Warning]")
            print(p4e)
            return "RevertSuccess"
        if "file(s) not opened" in str(p4e) or "file(s) up-to-date" in str(p4e):
            cmdParams = ["opened"]
            result = oP4.run(cmdParams)
            if len(result) == 0:
                print("[Info] All Files reverted. No files to submit.")
                return "AllRevert"
            else:
                return "NoFileRevert"
        else:
            print("[Error] Revert files in exclude path Failed. Path is: ")
            print("=========lRevertPath==========")
            print(lRevertPath)
            print("=========Finish==========")
            return "RevertError"

# scan those files locked manually
def revertLockedFiles(oP4, dChange, sSrcBranch, sDestBranch, sAdminUser, lRobotAccounts, sChangelist):
    lFile = []
    sResult = "Success"
    lResult = oP4.run("opened", "-c", "default")
    for dEle in lResult:
        lFile.append(dEle['depotFile'])
    if lFile:
        lResult = oP4.run("fstat", lFile)
        for dEle in lResult:
            if 'otherLock' in dEle.keys():
                sLockFile = dEle['depotFile']
                oP4.run("revert", sLockFile)
                # inform user
                handleLockedFile(sLockFile, sSrcBranch, sDestBranch, sChangelist, False)
                sResult = "Failed"
    return sResult

# Try to Submit the Change
def tryToSubmit(oP4, dChange, sAdminUser, lRobotAccounts, sSrcBranch, sDestBranch):
    try:
        bSuccess = True
        sResult = revertLockedFiles(oP4, dChange, sSrcBranch, sDestBranch, sAdminUser, lRobotAccounts, sChangelist)
        if sResult == "Failed":
            bSuccess = False
        oP4.run('submit', '-f', 'revertunchanged', '-d', dChange["Desc"])
        print("[Info] Submit from <{}> to <{}> Successfully.".format(sSrcBranch, sDestBranch))
        print("[Info] Changelist: " + sChangelist)
        print("[Info] nDescription：: " + dChange["Desc"].split('description: ')[-1])
        return bSuccess

    except P4.P4Exception as p4e:
        # Conflict files notify users
        if "Warnings during command execution" in str(p4e):
            print("[Warning]")
            print(p4e)
            return True
        if "No files to submit from the default changelist." in str(p4e):
            print("[Warning]")
            print(p4e)
            return True
        elif "File(s) couldn't be locked." in str(p4e):
            print("[Error]")
            print(p4e)
            sMsg = '[AutoMerge]Files be locked when submitting!\nStream <{}> To <{}>'.format(sSrcBranch, sDestBranch)
            SendMsgToAdminGroup(sMsg)
            raise
        else:
            print("[Error] Submit Failed in {} branch!".format(sDestBranch))
            print(p4e)
            sMsg = '[AutoMerge]Unexpected error when submit!\nStream <{}> To <{}>'.format(sSrcBranch, sDestBranch)
            SendMsgToAdminGroup(sMsg)
            return False

# Send Message to user when there is a Conflict
def handleConflict(oP4, dChange, sAdminUser, lRobotAccounts, sSrcBranch, sDestBranch):
    lSend = []
    lResult = []
    try:
        lResult = oP4.run("resolve", "-n")
    except P4.P4Exception as p4e:
        if "No file(s) to resolve." in str(p4e):
            pass
    try:
        confilctCount = 0
        destUser = ""
        fromUser = ""
        filesdes = []
        if len(lResult) > 0:
            print("[Info] ========== Conflict Files ========")

            for dEle in lResult:
                sFromFileOrg = dEle['fromFile']
                sFromFile = sFromFileOrg.replace(sSrcBranch, dChange['FromStream'])
                sClientFile = dEle['clientFile']
                # replace @ and # as %40 and %23
                if '@' in sClientFile:
                    sClientFile = sClientFile.replace('@', '%40')
                if '#' in sClientFile:
                    sClientFile = sClientFile.replace('#', '%23')
                print(sClientFile)
                sDepotFile = oP4.run("where", sClientFile)[0]['depotFile']
                if dChange["FromStream"]:
                    sFromFile.replace(sSrcBranch, dChange["FromStream"])
                # generate files and users dictionary
                dSend = generateFileUserDic(sFromFile, sFromFileOrg, sDepotFile, True, False)
                destUser = dSend.get("DestUser")
                fromUser = dSend.get("FromUser")
                lSend.append(dSend)
                print("[Info] Source File: " + dSend['FromFile'])
                print("[Info] Source File User: " + dSend['FromUser'])
                print("[Info] Destination File: " + dSend['DestFile'])
                print("[Info] Destination File User: " + dSend['DestUser'])
                newConflictToDB(dSend, sChangelist, "C")
                confilctCount = confilctCount + 1
                oP4.run("revert", dSend['DestFile'])
                filesdes.append(sFromFile)
            sendConflictMsgToGroup(sSrcBranch, sDestBranch, sChangelist, confilctCount, destUser, fromUser)
            sendMsgToConflictUser(sSrcBranch, sDestBranch, sChangelist, fromUser, filesdes)
            print("[Info] ========== Conflict Files Done ========")
            return False
        else:
            return True
    except P4.P4Exception as p4e:
        if "Warnings during command execution" in str(p4e):
            print("[Warning]")
            print(p4e)
            return True

def handleLockedFile(locked_file, sSrcBranch, sDestBranch, sChangelist, is_exclusive_file):
    sFromFile = locked_file.replace(sDestBranch, sSrcBranch)
    dSend = generateFileUserDic(sFromFile, sFromFile, locked_file, is_exclusive_file, True)
    newConflictToDB(dSend, sChangelist, "L")

def generateFileUserDic(sFrom, sFromOrg, sDest, is_exclusive_file, getlockuser):
    sFromUser = ''
    sDestUser = ''
    result = oP4.run("changes", sFrom)
    if result:
        sFromUser = result[0]['user']
    result = oP4.run("changes", sDest)
    if result:
        sDestUser = result[0]['user']

    # Get who is locking the file
    if getlockuser:
        param = 'otherOpen' if is_exclusive_file else 'otherLock'
        other_lock = oP4.run('fstat', sDest)[0].get(param)
        if other_lock:
            for lockUser in other_lock:
                if lockUser and "@" in lockUser:
                    sDestUser = lockUser.split("@")[0]

    dSend = {"FromFile": sFrom, "FromFileOrg": sFromOrg, "FromUser": sFromUser, "DestFile": sDest,
             "DestUser": sDestUser}
    return dSend

def GetDestUser(sDest, is_exclusive_file):
    param = 'otherOpen' if is_exclusive_file else 'otherLock'
    other_lock = oP4.run('fstat', sDest)[0].get(param)
    if other_lock:
        for lockUser in other_lock:
            if lockUser and "@" in lockUser:
                return lockUser.split("@")[0]
    return ""

def getStreamPath(depot_file):
    stream_path = depot_file.split("/")[3]
    relative_file_path = depot_file.replace("%s/" % stream_path, "")
    return relative_file_path, stream_path

def newConflictToDB(dSend, sChangelist, status):
    # url是web端创建冲突的接口
    url = "http://10.1.60.6:8095/api/branch_status/new_conflict"
    source_file = dSend.get("FromFileOrg")
    target_file = dSend.get("DestFile")
    relative_source_path, source_branch = getStreamPath(source_file)
    relative_target_path, target_branch = getStreamPath(target_file)

    print("source_branch >>> " + source_branch)
    print("target_branch >>> " + target_branch)
    print("relative_source_path >>> " + relative_source_path)
    print("relative_target_path >>> " + relative_target_path)

    data = dict(
        file_path=relative_source_path,
        source_file=source_file,
        target_file=target_file,
        source_branch=source_branch,
        target_branch=target_branch,
        source_user=dSend.get("FromUser"),
        target_user=dSend.get("DestUser"),
        changelist=sChangelist,
        status=status
    )

    print(data)

    r = requests.post(url, json=data)
    if r.status_code == requests.codes.ok:
        print(r.text)
    else:
        raise Exception("@new_conflict_to_db - New Conflict Error: Return Code = %s" % r.status_code)


def sendMsgToConflictUser(sSrcBranch, sDestBranch, sChangelist, fromUser, filesdes):
    fileStr = ""
    for it in filesdes:
        if len(fileStr) > 0:
            fileStr = fileStr + "\n"
        fileStr = fileStr + it
    print("[Info] ======== Sending Message to Conflict Users ======")
    sMsg = \
        '''**警告！检测到你的文件发生合并冲突，请迅速解决！**
        <font color=\"warning\">【合并方向】</font>%s → %s <font color=\"warning\">（请按此路径进行合并）</font>
        changelist：%s
        【文件列表】%s 
        <font color=\"warning\">【[如不会合并操作，点击此处](%s)</font><font color=\"info\">】</font>
        <font color=\"comment\">【[冲突汇总网页，点击此处](%s)</font><font color=\"info\">】网页中不再包含自己的冲突信息即为冲突解决</font>
        ''' \
        % (sSrcBranch, sDestBranch, sChangelist, fileStr, sMergeUrl, sConflictPage)
    SendMsgToUser(sMsg, fromUser)
    print("[Info] ======== Sending Message to Conflict Users Done ======")

def sendConflictMsgToGroup(sSrcBranch, sDestBranch, sChangelist, count, destUser, fromUser):
    print("[Info] ======== Sending Conflict Message to Group ======")
    sMsg = genConflictMsg(sSrcBranch, sDestBranch, count, sChangelist, destUser)
    print("[Info] Msg: " + sMsg)
    SendMsgToGroup(sMsg)
    print("[Info] ======== Sending Conflict Message to Group Done ======")

def sendMsgToLockedUser(exclusiveFiles, sSrcBranch, sDestBranch, sChangelist):
    users = {}
    for it in exclusiveFiles:
        if not users.get(it[1]):
            users[it[1]] = []
        if not it[0] in users[it[1]]:
            users[it[1]].append(it[0])

    for it in users:
        files = users[it]
        user = it
        fileStr = ""
        for file in files:
            if len(fileStr) > 0:
                fileStr = fileStr + "\n"
            fileStr = fileStr + file
        sMsg = \
            '''** 警告！检测到文件合并时被你【锁定】，合并失败，请迅速解决！**
            <font color=\"info\">【解决方式】1、解锁%s上被锁的文件；2、手动合并后提交</font>
            <font color=\"warning\">【合并方向】%s → %s （请按此路径进行合并）</font>
            【合并changelist】%s
            【锁定文件】%s
            <font color=\"warning\">【[如不会合并操作，点击此处](%s)</font><font color=\"info\">】</font>
            <font color=\"comment\">【[冲突汇总网页，点击此处](%s)</font><font color=\"info\">】网页中不再包含自己的冲突信息即为冲突解决</font>
            ''' \
            % (
                sDestBranch, sSrcBranch, sDestBranch, sChangelist, fileStr, sMergeUrl,
                sConflictPage)
        SendMsgToUser(sMsg, user)

def sendMsgToLockerGroup(exclusive_files, sSrcBranch, sDestBranch, sChangelist):
    print("[Info] ======== Sending Message to Locked Users ======")
    sMsg = genLockMsg(sSrcBranch, sDestBranch, sChangelist, exclusive_files)
    print("[Info] Msg: " + sMsg)
    SendMsgToGroup(sMsg)
    print("[Info] ======== Sending Message to Locked Users Done ======")

# 需要管理员定期巡查
def SendMsgToAdminGroup(msg):
    url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=e271a571-cdb9-4fde-ae9a-c5ce2d06dcba"
    jsondata = {
        "markdown": {
            "content": msg,
            "mentioned_list": ['@all'],
        },
        "msgtype": "markdown",
    }
    resp = requests.post(url, data=json.dumps(jsondata))
    print(resp.text)

# 需要团队成员修正
def SendMsgToGroup(msg):
    url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=295c3a45-4e4d-48bf-971c-f70af6d2430c"
    jsondata = {
        "markdown": {
            "content": msg,
            "mentioned_list": ['@all'],
        },
        "msgtype": "markdown",
    }
    resp = requests.post(url, data=json.dumps(jsondata))
    print(resp.text)

def SendMsgToUser(msg, user):
    if user != None and len(user) > 0:
        resp = requests.post(url="http://10.1.60.6:8095/api/wxpush/app_xiaofuzong/message/send",
                      json={
                          "touser": user,
                          "msgtype": "markdown",
                          "content": msg
                    })
        print(resp.text)

def genConflictMsg(sSrcBranch, sDestBranch, filesCount, sChangelist, DestUser):
    sMsg = \
        '''**警告！检测到你的文件发生合并冲突，请迅速解决！**
        <font color=\"warning\">【合并方向】</font>%s → %s <font color=\"warning\">（请按此路径进行合并）</font>
        【冲突文件数量】%s changelist：%s
        【%s最后提交者】%s 
        <font color=\"warning\">【[如不会合并操作，点击此处](%s)</font><font color=\"info\">】</font>
        <font color=\"comment\">【[冲突汇总网页，点击此处](%s)</font><font color=\"info\">】网页中不再包含自己的冲突信息即为冲突解决</font>
        ''' \
        % (sSrcBranch, sDestBranch, filesCount, sChangelist, sDestBranch, DestUser, sMergeUrl, sConflictPage)
    return sMsg

def genLockMsg(sSrcBranch, sDestBranch, sChangelist, exclusiveFiles):
    files = []
    users = []
    filesStr = ""
    usersStr = ""
    for it in exclusiveFiles:
        if not it[0] in files:
            files.append(it[0])
            filesStr = filesStr + it[0]
        if not it[1] in users:
            if len(users) > 0:
                usersStr = usersStr + ","
            users.append(it[1])
            usersStr = usersStr + it[1]
    sMsg = \
        '''** 警告！检测到文件合并时被你【锁定】，合并失败，请迅速解决！**
        <font color=\"info\">【解决方式】1、解锁%s上被锁的文件；2、手动合并后提交</font>
        <font color=\"warning\">【合并方向】%s → %s （请按此路径进行合并）</font>
        【合并changelist】%s
        【%s文件锁定者】%s 
        <font color=\"warning\">【[如不会合并操作，点击此处](%s)</font><font color=\"info\">】</font>
        <font color=\"comment\">【[冲突汇总网页，点击此处](%s)</font><font color=\"info\">】网页中不再包含自己的冲突信息即为冲突解决</font>
        ''' \
        % (
            sDestBranch, sSrcBranch, sDestBranch, sChangelist, sDestBranch, usersStr, sMergeUrl,
            sConflictPage)
    return sMsg

# Clean up the pending changlists after merge finished. No Matter success or not
def cleanUp(oP4):
    print("[Info] Cleaning up pendings")
    try:
        oP4.run('revert', '//...')
    except P4.P4Exception as p4e:
        if "Warnings during command execution" in str(p4e):
            print("===[Warning]===")
            print(p4e)
        else:
            print(p4e)
            raise
    try:
        oP4.run('sync', '//...#head')
    except P4.P4Exception as p4e:
        if "Warnings during command execution" in str(p4e):
            print("===[Warning]===")
            print(p4e)
        else:
            print(p4e)
            raise

if __name__ == "__main__":
    oParser = argparse.ArgumentParser()
    oParser.add_argument('-s', dest='sourceBranch')
    oParser.add_argument('-d', dest='destBranch')
    oParser.add_argument('-c', dest='changelist')
    oParser.add_argument("-f", dest='bFull')

    oArgs = oParser.parse_args()

    sSrcBranch = oArgs.sourceBranch
    sDestBranch = oArgs.destBranch
    sChangelist = oArgs.changelist
    bFull = oArgs.bFull

    oP4 = P4.P4()
    oP4.exception_level = 1
    oP4.user = os.environ.get("P4_USER", None)
    oP4.password = os.environ.get("P4_PASSWD", None)
    oP4.client = os.environ.get("P4_CLIENT", None)
    oP4.port = os.environ.get("P4_PORT", None)
    oP4.charset = "utf8"
    oP4.api_level = 85
    oP4.connect()
    sAdminUser = os.environ['ADMIN_USER']
    lRobotAccounts = os.environ.get("ROBOT_ACCOUNTS", "").split(",")
    lRevertPath = os.environ.get("EXCLUDE_PATH", "").split(",")

    exit(merge_branch(sSrcBranch, sDestBranch, sChangelist, sAdminUser, lRobotAccounts, lRevertPath, bFull))
