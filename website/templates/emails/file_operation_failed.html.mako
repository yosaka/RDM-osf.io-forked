<!doctype html>
<%!
    from website import settings
%>
<html class="no-js" lang="">
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title>NII Email Notification Template</title>
    <meta name="description" content="National Institute of Informatics Notifications">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body leftmargin="0" marginwidth="0" topmargin="0" marginheight="0" offset="0" style="-webkit-text-size-adjust: none;font-family: 'Helvetica', sans-serif;background: #eeeeee;padding: 0;margin: 0;border: none;list-style: none;width: 100% !important;">
<table id="layout-table" width="100%" border="0" cellpadding="0" cellspacing="0">
    <tr>
        <td style="border-collapse: collapse;">
            <table id="layout-table" width="100%" border="0" cellpadding="10" cellspacing="0" height="100%">
                <tbody>
                    <tr class="banner" style="background: #214762;color: white;">
                        <td class="text-center" style="border-collapse: collapse;text-align: center;">
                            <table id="header-logo" border="0" style="margin: 0 auto;padding: 0px;">
                                <tr>
                                    <td style="border-collapse: collapse;">
                                        % if context.get('logo', settings.OSF_LOGO) not in settings.OSF_LOGO_LIST:
                                            <img src="https://raw.githubusercontent.com/CenterForOpenScience/osf-assets/master/files/preprints-assets/${context.get('logo')}/wide_white.png" alt="GakuNin RDM logo" style="border: 0;height: auto;line-height: 100%;outline: none;text-decoration: none;">
                                        %else:
                                            <img src="https://rdm.nii.ac.jp/static/img/${context.get('logo', settings.OSF_LOGO)}.png" alt="GakuNin RDM logo" style="border: 0;height: auto;line-height: 100%;outline: none;text-decoration: none;">
                                        % endif
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </tbody>
            </table>
        </td>
    </tr>
    <tr>
        <td style="border-collapse: collapse;">
            <table id="content" width="600" border="0" cellpadding="25" cellspacing="0" align="center" style="margin: 30px auto 0 auto;background: white;box-shadow: 0 0 2px #ccc;">
                <tbody>
                    <tr>
                        <td style="border-collapse: collapse;">
                            <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Recent Activity</h3>
                        </td>
                    </tr>
                    <tr>
                        <th colspan="2" style="padding: 0px 15px 0 15px">
                            <h3 style="padding: 0 15px 5px 15px; margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300; border-bottom: 1px solid #eee; text-align: left;">
                              ${destination_node.title}
                              %if destination_node.parent_node:
                                <small style="font-size: 14px;color: #999;"> in ${destination_node.parent_node.title} </small>
                              %endif
                            </h3>
                        </th>
                    </tr>
                </tbody>
                <tbody>
                    <tr>
                        <td style="border-collapse: collapse;">
                          An error has occurred, and the ${'folder' if source_path.endswith('/') else 'file'} from ${source_node.title} on the GakuNin RDM was not successfully ${'moved' if action == 'move' else 'copied'}.
                          Please log in and try this action again. If the problem persists, please email ${osf_support_email}.
                        </td>
                    </tr>
                </tbody>
            </table>
        </td>
    </tr>
    <tr>
        <td style="border-collapse: collapse; padding-top: 15px;">
            <table width="80%" border="0" cellpadding="10" cellspacing="0" align="center" class="footer" style="margin-top: 45px;padding: 25px 0 35px;background-color: rgb(244, 244, 244);border-top: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;width: 100%;color: #555;">
                <tbody>
                    <tr>
                        <td style="border-collapse: collapse;">
                            <p class="small text-center" style="text-align: center;font-size: 12px;">Copyright &copy; 2018National Institute of Informatics, All rights reserved. |
                                    <a href="https://support.rdm.nii.ac.jp/terms/">Privacy Policy</a></p>
                            <p class="text-smaller text-center" style="text-align: center;font-size: 12px;">2-1-2 Hitotsubashi, Chiyoda Ward, Tokyo 101-8430, JAPAN</p>
                        </td>
                    </tr>
                </tbody>
            </table>
        </td>
    </tr>
</table>
</body>
</html>
