<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    ID: ${user._id}<br>
    <br>
    プロフィール: ${user.absolute_url}<br>
    <br>
    プライマリメール: ${user.username} <br>

</tr>
<tr>
  <td style="border-collapse: collapse;">
    ID: ${user._id}<br>
    <br>
    Profile: ${user.absolute_url}<br>
    <br>
    Primary Email: ${user.username} <br>

</tr>
</%def>
