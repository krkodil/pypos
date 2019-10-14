# pypos
POS and ECR related tools

<h3>datecs.py</h3>
 Quick draft of Datecs protocol for ECR
 <ul>
    <li>Support all old devices (OLD legacy protocol):<br>
        &nbsp; DP-05, DP-25, DP-35, WP-50, DP-150 
    </li>    
    <li>Support new 'X' devices (X protocol):<br>
         &nbsp; FMP-350X, FMP-55X, FP-700X, WP-500X, WP-50X, DP-25X, DP-150X, DP-05C
    </li>        
    <li>Serial connector (RS232)</li>        
    <li>Ethernet connector (TCP/IP)</li>
 </ul>
 <br> 
 Serial connection:
 <pre>
    fd = DatecsFiscalDevice(EthernetConnector('192.168.0.36', 4999), DatecsProtocol.X)
    if fd.connect():
    fd.set_date_time(datetime.now()):
    print('ECR DateTime is:', fd.get_date_time())
    fd.disconnect()
</pre>
 <br> 
 Ethernet connection:
 <pre>
    fd = DatecsFiscalDevice(SerialConnector('COM1', 115200), DatecsProtocol.OLD)
    if fd.connect():
    fd.set_date_time(datetime.now()):
    print('ECR DateTime is:', fd.get_date_time())
    fd.disconnect()
 </pre>