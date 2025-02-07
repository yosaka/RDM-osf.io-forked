<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    We just wanted to let you know that ${initiated_by} has initiated a request to end the embargo for a registration of ${project_name}. That registration can be viewed here: ${registration_link}.<br>
    <br>
    If approved, the embargo will be terminated and the registration and all of its components will be made public immediately.<br>
    <br>
    Sincerely yours,<br>
    <br>
    The GRDM Robots<br>

</tr>
</%def>
