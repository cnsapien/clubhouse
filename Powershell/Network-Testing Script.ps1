cls
write-host -BackgroundColor Blue "##########################"
write-host "Network Testing Script"     
write-host "`n"
write-host "Made by:"
write-host "`n"
Write-Host "Crow's It Department"
write-host "`n"
write-host -BackgroundColor Blue "##########################"

write-host "`n"
write-host -BackgroundColor Gray "What this thing do?"
write-host "`n"
write-host "This script will 'Ping' each computer for 2 times 
            `n and write the result in a colorable answer"

write-host "`n"

write-host "Have fun"

write-host "`n"

                                   


$crowspc = (Read-Host -Prompt "Please write the computer names of the pc's you want to check, with comma seporated (you can combine IP's and pc's to: 192.168.2.1,pc-01 etc..)").split(',') | ForEach-Object {$_.trim()}


         
         foreach ($pc in $crowspc) {
         
          if (Test-Connection -computername $pc -Count 2 -Quiet) 

          {write-host -BackgroundColor green -ForegroundColor Blue "`nThe connection to ->$pc<- is OK :) !!!" }
          
          else { write-host -BackgroundColor Red -ForegroundColor DarkYellow "`nThe Connection to ->$pc<- is not good :( !! "}

          }
        

          write-host "`n"
          
          pause