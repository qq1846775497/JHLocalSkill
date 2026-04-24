#  -*- coding: utf-8 -*-
import P4
import os
import re
import argparse
import requests
import json
#from desWorker import *
from P4RevertOtherUserOpenedFile import *

# exit Code
# 0: success/no need to merge
# 1: files locked when copy
# 96: error when resolve river crab, file locked
# 97: error when submit to p4 after river crab
# 98: error when get latest changelist from source branch
# 99: error when switch branch
# 100: has exception when switching stream or run copy command
# 101: has exception when generate change
# 102: has exception when resolve file automatically (no merging)
# 103: has exception when revert file in exclude path
# 104: other exceptions

def updateBranch(sSrcBranch, sDestBranch, sChangelist, sAdminUser, lRevertPath, sRoot):
    # 开局清理copy/合并用文件夹
    clean_up(oP4, False)

    try:
        bStream = os.environ.get("IS_STREAM", "true")
        if bStream == "true":
            oP4.run('client', '-s', '-S', "//{}/".format(sRoot) + sDestBranch)
    except P4.P4Exception as p4e:
        print("[Error] Copy from <{}> to <{}> failed.".format(sSrcBranch, sDestBranch))
        print("[Error] " + str(p4e))
        clean_up(oP4)
        return 99
    revertOtherUserOpenedFile = P4RevertOtherUserOpenedFile()
    revertOtherUserOpenedFile.SetNeedLogin(False)
    revertOtherUserOpenedFile.SetNeedRevertOther(True)
    revertOtherUserOpenedFile.SetNeedUnlockOther(True)
    revertOtherUserOpenedFile.SetP4(oP4)
    searchServerPath = "//NXX_Stream/" + sDestBranch + "/..."
    searchServerPathPrefix = "//NXX_Stream/" + sDestBranch + "/"
    revertOtherUserOpenedFile.SetSearchServerPath(searchServerPath)
    revertOtherUserOpenedFile.SetSearchServerPathPrefix(searchServerPathPrefix)
#    revertOtherUserOpenedFile.Init()
#    revertOtherUserOpenedFile.LogInfo()
#    revertOtherUserOpenedFile.Run()

    bIsFailing = False
    sPattern = r'(.*)\s\-\scan\'t\sintegrate\sexclusive\sfile\salready\sopened'
    oMatch = re.compile(sPattern)

    if sDestBranch == '':
        sMsg = '参数异常, 目标分支为空.\n源分支{}@{}无法进行拷贝.'.format(sSrcBranch, sChangelist)
        print("[Info] No Destination Stream. Won\'t copy")
        SendMsgToBot(sMsg, sAdminUser)
        return 0
    try:
        oP4.run('copy', '-F', "//{}/".format(sRoot) + sSrcBranch + '/...@' + sChangelist,"//{}/".format(sRoot) + sDestBranch + '/...')
        exclusives = []
        for dResult in oP4.warnings:
            if isinstance(dResult, str) and oMatch.match(dResult):
                exclusive_file = oMatch.match(dResult).groups()[0]
                print(exclusive_file)
                sWorkspace = oP4.run('fstat', exclusive_file)[0]['otherOpen'][0]
                print(''.join(['Exclusive file: ', exclusive_file, ' is locked in workspace: ', sWorkspace]))
                exclusives.append([exclusive_file, GetDestUser(exclusive_file, True)])
        if len(exclusives) > 0:
            sMsg = gen_lock_msg(sSrcBranch, sDestBranch, exclusives)
            SendMsgToBot(sMsg, sAdminUser)
            clean_up(oP4)
            return 1
    except P4.P4Exception as p4e:
        clean_up(oP4)
        if "File(s) up-to-date" in str(p4e):
            print("[Warning] " + str(p4e))
            return 0
        else:
            print("[Error] Copy from <{}> to <{}> failed.".format(sSrcBranch, sDestBranch))
            print("[Error] " + str(p4e))
            return 100

    dChange = generate_change(sSrcBranch, sDestBranch, sChangelist)
    if not dChange:
        sMsg = "[Error] Generate Change failed when copy from <{}> to <{}>.".format(sSrcBranch, sDestBranch)
        print(sMsg)
        SendMsgToBot(sMsg, sAdminUser)
        clean_up(oP4)
        return 101

    print("revertPath : {}".format(lRevertPath))
    # revert exclude path
    if len(lRevertPath) > 0 and lRevertPath[0] != '':
        print("revertPath : {}".format(lRevertPath))
        sResult = revert_exclude(oP4, lRevertPath)
        print("[Debug] sResult: " + sResult)
        if sResult == "AllRevert":
            sMsg = "[Info] All Files reverted when copy from <{}> to <{}>.".format(sSrcBranch, sDestBranch)
            print(sMsg)
            clean_up(oP4)
            return 0
        # elif bResult == "RevertSuccess":
        #     pass
        # elif bResult == "NoFileRevert":
        #     pass
        elif sResult == "RevertError":
            sMsg = "Revert exclude files failed when copy from <{}> to <{}>.".format(sSrcBranch, sDestBranch)
            SendMsgToBot(sMsg, sAdminUser)
            clean_up(oP4)
            return 102

    if not bIsFailing:
        bResult = try_2_submit(oP4, dChange, sAdminUser)
        if bResult:
            return 0
        else:
            sMsg = "[Error] Submit change failed when copy from <{}> to <{}>.".format(sSrcBranch, sDestBranch)
            print(sMsg)
            SendMsgToBot(sMsg, sAdminUser)
            return 103
    else:
        sMsg = "[Error] Some Files are locked when copy from <{}> to <{}>.".format(sSrcBranch, sDestBranch)
        print(sMsg)
        SendMsgToBot(sMsg, sAdminUser)
        clean_up(oP4)
        return 1


def gen_lock_msg(sSrcBranch, sDestBranch, exclusiveFiles):
    files = []
    users = []
    filesStr = ""
    usersStr = ""
    for it in exclusiveFiles:
        if not it[0] in files:
            filesStr = filesStr + "\n"
            files.append(it[0])
            filesStr = filesStr + it[0]
        if not it[1] in users:
            if len(users) > 0:
                usersStr = usersStr + ","
            users.append(it[1])
            usersStr = usersStr + it[1]
    sMsg = \
        '''** 警告！从%s copy 到 %s时，因文件锁定，copy失败，请迅速解决！**
        <font color=\"info\">【解决方式】解锁%s上被锁的文件；</font>
        【%s文件锁定者】%s 
        【锁定文件列表】%s 
        ''' \
        % (
            sSrcBranch, sDestBranch, sDestBranch,sDestBranch, usersStr, filesStr)
    return sMsg

def GetDestUser(sDest, is_exclusive_file):
    param = 'otherOpen' if is_exclusive_file else 'otherLock'
    other_lock = oP4.run('fstat', sDest)[0].get(param)
    if other_lock:
        for lockUser in other_lock:
            if lockUser and "@" in lockUser:
                return lockUser.split("@")[0]
    return ""

def SendMsgToBot(msg, adminuser):
#   url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=7f66f992-7454-42f8-8a01-b9bf96d231ad"
#   url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=bacc657b-49e2-4463-874a-3604e9153b80xx"
#   url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=97eeceef-1324-4442-be69-ff5d50f51480"
    url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=295c3a45-4e4d-48bf-971c-f70af6d2430c"
    jsondata = {
        "markdown": {
            "content": msg,
            "mentioned_list": ['@all'],
        },
        "msgtype": "markdown",
    }
    resp = requests.post(url, data=json.dumps(jsondata))

    print("send msg")
    print(resp.text)

# Generate a Pending Change in default pending changelist by the original changelist.
def generate_change(sSrcBranch, sDestBranch, sChangelist):
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

#        sDesc = "{}\nuser: {}\ndescription: {}\nstream: {}\nchange: {}".format("[原始提交]", sUser, sDesc,
#                                                                               sFromStream, schange)
        #sDesc = desWorker.genDes(sDesc, sUser, schange, sFromStream)
        print(sDesc)
        return {'User': sUser, 'Issue': "", 'Desc': sDesc, 'FromStream': sFromStream}

    except P4.P4Exception as p4e:
        print("[Error]" + str(p4e))
        print("EEEEEE")
        # clean_up(oP4)
        return None


def revert_exclude(oP4, lRevertPath):
    try:
        # for e in lRevertPath:


        cmdParams = ['revert', '-w', lRevertPath]
        res = oP4.run(cmdParams)
        print("Revert Path {} Res: {}".format(lRevertPath, res))
        cmdParams = ["opened"]
        result = oP4.run(cmdParams)
        if len(result) == 0:
            print("[Info] All Files reverted. No files to submit.")
            return "AllRevert"
        return "RevertSuccess"
    except P4.P4Exception as p4e:
        if "file(s) not opened" in str(p4e) or "file(s) up-to-date" in str(p4e):
            print("[Warning] " + str(p4e))
            return "NoFileRevert"
        else:
            print("[Error] Revert files in exclude path Failed. Path is: ")
            print("=========lRevertPath==========")
            print(lRevertPath)
            print("=========Finish==========")
            return "RevertError"


def try_2_submit(oP4, dChange, sAdminUser):
    try:
        oP4.run('submit', '-f', 'revertunchanged', '-d', dChange['Desc'])
        print('[Info] Copy Successfully.')
        sMsg = '从<{}>拷贝到<{}>成功\n\nChangelist: {}。\nDescription：{}' \
            .format(sSrcBranch, sDestBranch, sChangelist, dChange['Desc'].split('description: ')[-1])
        print("[Info] " + sMsg)
        clean_up(oP4)
        return True

    except P4.P4Exception as p4e:
        print(p4e)
        if "No files to submit from the default changelist." in str(p4e):
            print("[Warning]")
            print(p4e)
            return True
        print("[Error] Someone has files locked in {} branch, run p4 copy manually to find out more details!".format(
            sDestBranch))
        sMsg = '从<{}>拷贝到<{}>失败，有文件被锁，请确认。\n\nChangelist: {}。\nDescription: {}' \
            .format(sSrcBranch, sDestBranch, sChangelist, dChange['Desc'].split('description: ')[-1])
        print("[Error] " + str(p4e))
        print('-_,-Verbose Error Output:')
        for msg in oP4.messages:
            print(msg)
        SendMsgToBot(sMsg, sAdminUser)
        # cleaning up
        clean_up(oP4)
        return False


def clean_up(oP4, disconnect_flag=True):
    print("[Info] Revert modify")
    try:
        oP4.run('revert', '//...')
    except P4.P4Exception as p4e:
        if "Warnings during command execution" in str(p4e):
            print("[Warning]")
            print(p4e)
        else:
            print(p4e)
            raise
    try:
        oP4.run('sync', '//...#0')
    except P4.P4Exception as p4e:
        if "Warnings during command execution" in str(p4e):
            print("[Warning]")
            print(p4e)
        else:
            print(p4e)
            raise
    if disconnect_flag:
        oP4.disconnect()


def process_river_crab(oP4, crab_list, sDestBranch):
    oP4.exception_level = 1
    if not oP4.connected():
        oP4.connect()
    changelist = crab_list.split(',')
    changelist.sort()
    locked_file = []
    print('[Info] Going to cook river crab with: {}'.format(str(changelist)))
    warning_flag = False
    lock_mark = r'\+.*l'
    for cl in changelist:
        if not cl.isdigit():
            print('[Warning] Invalid input detected! CL:{}'.format(cl))
            warning_flag = True
            continue
        change_list = oP4.run('describe', '-s', cl)
        if len(change_list) > 0:
            change = change_list[0]
            depot_file = change['depotFile']
            file_rev = change['rev']
            file_action = change['action']
            if len(depot_file) > 0:
                print('[Info] =======Start checkout CL: {}======='.format(cl))
                for i in range(len(depot_file)):
                    if '//{}/{}'.format(sRoot, sDestBranch) not in depot_file[i]:
                        print('[Warning] File in Changelist {} not belongs to //{}/{}.\nFile Path: {}'
                              .format(cl, sRoot, sDestBranch, depot_file[i]))
                        warning_flag = True
                        break
                    oP4.run('revert', '-w', depot_file[i])
                    file_stat = oP4.run('fstat', '{}#{}'.format(depot_file[i], file_rev[i]))
                    if len(file_stat) > 0:
                        single_file = file_stat[0]
                        local_path = single_file['clientFile']
                        if 'otherOpen' in single_file.keys() and re.search(lock_mark, single_file['headType']):
                            locked_file.append(depot_file[i])
                            continue
                        elif 'otherLock' in single_file.keys():
                            locked_file.append(depot_file[i])
                            continue
                    else:
                        print('[Warning] Get local path failed!!\nFile Path:{}'.format(depot_file[i]))
                        warning_flag = True
                        continue
                    oP4.run('sync', depot_file[i])
                    if file_action[i] == 'edit' or file_action[i] == 'add':
                        oP4.run('edit', depot_file[i])
                        if len(local_path) > 0:
                            oP4.run('print', '-o', local_path, '{}#{}'.format(depot_file[i], file_rev[i]))
                        else:
                            print('[Warning] Local path length ZERO!!\nFile Path:{}'.format(depot_file[i]))
                            warning_flag = True
                            continue
                    elif file_action[i] == 'delete':
                        oP4.run('delete', depot_file[i])
                    else:
                        print('[Warning] Unsupported action!! File Path: {} Action: {}'.format(depot_file[i], file_action[i]))
                        warning_flag = True
            else:
                print('[Warning] Get file list in CL {} failed!!'.format(cl))
                warning_flag = True
        else:
            print('[Warning] Get Change list info failed!!, CL:{}'.format(cl))
            warning_flag = True

    if len(locked_file) > 0:
        print('[Error]========Locked File List=======')
        for file in locked_file:
            print(file)
        print('[Error]======Total Num {}======='.format(len(locked_file)))
        clean_up(oP4)
        sMsg = '在{}回退资源提交失败, 有文件被锁定, 请检查日志. 回退CL:{}'.format(sDestBranch, crab_list)
        SendMsgToBot(sMsg, sAdminUser)
        exit(96)
    if warning_flag:
        sMsg = '在{}回退资源过程中出现异常, 请注意检查日志, 回退CL:{}'.format(sDestBranch, crab_list)
        SendMsgToBot(sMsg, sAdminUser)

    try:
        msg = 'passkey [NoMerge] 在{}分支回滚屏蔽资源{}'.format(sDestBranch, str(changelist))
        oP4.run('submit', '-f', 'revertunchanged', '-d', msg)
        print('[Info] Submit to {} with river crab success.'.format(sDestBranch))
        clean_up(oP4)
        exit(copy_result)
    except P4.P4Exception as p4e:
        print('[Error] Submit to {} failed after cook river crab.'.format(sSrcBranch))
        print("[Error] " + str(p4e))
        clean_up(oP4)
        sMsg = '在{}回退资源提交失败, 回退CL:{}'.format(sDestBranch, crab_list)
        SendMsgToBot(sMsg, sAdminUser)
        exit(97)


if __name__ == "__main__":
    oParser = argparse.ArgumentParser()
    oParser.add_argument('-s', dest='sourceBranch')
    oParser.add_argument('-d', dest='destBranch')
    oParser.add_argument('-c', dest='changelist')

    oArgs = oParser.parse_args()

    sSrcBranch = oArgs.sourceBranch
    sDestBranch = oArgs.destBranch
    sChangelist = oArgs.changelist

    oP4 = P4.P4()
    oP4.exception_level = 1
    oP4.user = os.environ['P4_USER']
    oP4.password = os.environ['P4_PASSWD']
    oP4.client = os.environ['P4_CLIENT']
    oP4.port = os.environ['P4_PORT']
    oP4.charset = "utf8"
    oP4.api_level = 85
    oP4.connect()
    sAdminUser = os.environ['ADMIN_USER']
    lRevertPath = os.environ.get("EXCLUDE_PATH", "").split(",")
    sRoot = os.environ.get("ROOT_DEPOT", "NXX_Stream")

    try:
        oP4.run('client', '-s', '-S', "//NXX_Stream/" + sDestBranch)
    except P4.P4Exception as p4e:
        print("[Error]" + str(p4e))


    if sChangelist == 'latest':
        try:
            latest_cl = oP4.run('changes', '-m', '1', '-s' 'submitted', '//{}/{}/...'.format(sRoot, sSrcBranch))
            print('P4 change result:' + str(latest_cl))
            if latest_cl is not None and len(latest_cl) > 0:
                sChangelist = latest_cl[0]['change']
            if sChangelist is None or len(sChangelist) == 0:
                print('[Error] Get latest changelist from {} failed'.format(sSrcBranch))
                oP4.disconnect()
                exit(98)
        except P4.P4Exception as p4e:
            print('[Error] Get latest changelist from {} failed'.format(sSrcBranch))
            print("[Error] " + str(p4e))
            oP4.disconnect()
            exit(98)

    copy_result = updateBranch(sSrcBranch, sDestBranch, sChangelist, sAdminUser, lRevertPath, sRoot)
    crab_list = os.environ.get('RIVER_CRAB_LIST', '')
    if len(crab_list) > 0 and copy_result == 0:
        process_river_crab(oP4, crab_list, sDestBranch)
    else:
        print('[Info] Nothing to cook or Copy failed.')
        exit(copy_result)
