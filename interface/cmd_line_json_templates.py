

def repeated_section(tpl, tag='result'):
    return "{.section %s}{.repeated section @}%s{.end}{.end}" % (tag, tpl)

#------------------------------------------------------------------------------ 

tpl_status = "{.section status}{@}{.end}"
tpl_result = repeated_section("{@}\n")
tpl_message = "{.section message}{@}{.end}"
tpl_errors = repeated_section("{@}\n", tag="errors")
tpl_execution = "{.section execution}: {@} sec.{.end}"

#------------------------------------------------------------------------------ 

TPL_JSON = "{@}"

#------------------------------------------------------------------------------ 

TPL_RAW = """{0}{1}
{2}{3}{4}
""".format(tpl_status, tpl_execution, tpl_result, tpl_message, tpl_errors)

#------------------------------------------------------------------------------ 

TPL_BACKUPS_LIST = """{0}{1}
{2}{3}
""".format(
    tpl_status,
    tpl_execution,
    repeated_section(
        "{id} {type} {size} {path} {.section versions}{.repeated section @}[{version}: {size} (#{blocks})]{.end}{.end}\n"
    ),
    tpl_errors)

TPL_BACKUPS_LIST_IDS = """{0}{1}
{2}{3}
""".format(
    tpl_status,
    tpl_execution,
    repeated_section("{backupid} {size} {path}\n"),
    tpl_errors)

TPL_BACKUPS_RUNNING_LIST = """{0}{1}
{2}{3}{4}
""".format(
    tpl_status,
    tpl_execution,
    repeated_section(
        "{backup_id} from {source_path} of total {total_size}, currently {bytes_processed} bytes processed, ready by {progress}%\n"
    ), 
    tpl_message,
    tpl_errors)

TPL_BACKUPS_TASKS_LIST = """{0}{1}
{2}{3}{4}
""".format(
    tpl_status,
    tpl_execution,
    repeated_section("{id}: {path_id} from {local_path} created at {created}\n"),
    tpl_message,
    tpl_errors)

#------------------------------------------------------------------------------ 

TPL_RESTORES_RUNNING_LIST = """{0}{1}
{2}{3}{4}
""".format(
    tpl_status,
    tpl_execution,
    repeated_section("{backup_id}, currently {bytes_processed} bytes processed\n"),
    tpl_message,
    tpl_errors)

#------------------------------------------------------------------------------ 

TPL_OPTIONS_LIST_KEY_TYPE_VALUE = """{0}{1}
{2}{3}
""".format(
    tpl_status,
    tpl_execution,
    repeated_section("{key} ({type}) : {value}\n"),
    tpl_errors)

#------------------------------------------------------------------------------ 

TPL_OPTION_MODIFIED = """{0}{1}
{2}{3}
""".format(
    tpl_status,
    tpl_execution,
    repeated_section("{key} ({type}) : {value}{.section old_value}, previous : {@}{.or}{.end}\n"),
    tpl_errors)

TPL_OPTION_SINGLE = """{0}{1}
{2}{3}
""".format(tpl_status, tpl_execution,
    repeated_section("{key} ({type}) : {value}{.section old_value}, previous : {@}{.or}{.end}\n"),
    tpl_errors)

#------------------------------------------------------------------------------ 

TPL_SUPPLIERS = """{0}{1}
{2}{3}""".format(
    tpl_status,
    tpl_execution,
    repeated_section("{position}: {idurl}, since {connected}, keeps {numfiles} files, {status}\n"),
    tpl_errors)

#------------------------------------------------------------------------------ 

TPL_FRIEND_LOOKUP = """{.section result}
friend lookup:
    {result}
    {nickname}
    {position}
    {idurl}
{.end}"""

TPL_FRIEND_LOOKUP_REPEATED_SECTION = """{.section result}
friends:
{.repeated section @}
    {idurl} : {nickname}
{.end}
{.end}"""

TPL_MESSAGE_SENDING = """{.section result}
    {@}
{.end}
{.section error}
    error: {@}
{.end}
    recipient: {.section recipient}{@}{.end}
"""

