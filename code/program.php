<?php
session_start();
/*currentfullcode will store a string that represents the users block code, condensed into a string
his is stored as a session variable, because each time a button is pressed it refreshes the page
returning to index.php clears the string */
//Here we append the session variable with a given string depending on which button was last pressed
//it is here that an array should be made spliting each part of the currentfullcode by commas
//once the array is made, the most recent 'command' can be inserted into the array at the correct location,
//the commands should then be updated with the correct number
if(isset($_POST['addStage'])) {
  $_SESSION['currentfullcode'] .= 'S{,';
}
?>
<!DOCTYPE html>
<head>
</head>
<?php //general styling, should definitely be updated with a fresh coat of paint ?>
<meta name="viewport" charset="UTF-8" content="width=device-width, initial-scale=1">
<style>
body {
  font-family: "Lato", sans-serif;
}

.sidenavL {
  width: 130px;
  position: fixed;
  z-index: 1;
  top: 20px;
  left: 10px;
  background: #eee;
  overflow-x: hidden;
  padding: 8px 0;
}

.sidenavR {
  width: 300px;
  position: fixed;
  z-index: 1;
  top: 20px;
  right: 10px;
  background: #eee;
  overflow-x: hidden;
  padding: 8px 0;
}

.sidenavL p {
  padding: 6px 8px 6px 16px;
  text-decoration: none;
  font-size: 25px;
  color: #2196F3;
  display: block;
}

.sidenavL a {
  padding: 6px 8px 6px 16px;
  text-decoration: none;
  font-size: 25px;
  color: #2196F3;
  display: block;
}

.sidenavR p {
  padding: 6px 8px 6px 16px;
  text-decoration: none;
  font-size: 25px;
  color: #2196F3;
  display: block;
}

.sidenavL a:hover {
  color: #064579;
}

.sidenavR a:hover {
  color: #064579;
}

.main {
  margin-left: 140px;
  margin-right: 140px; /* Same width as the sidebar + left position in px */
  font-size: 28px; /* Increased text to enable scrolling */
  padding: 0px 10px;
}

@media screen and (max-height: 450px) {
  .sidenav {padding-top: 15px;}
  .sidenav a {font-size: 18px;}
}
</style>



<body>

<?php /*The Left sidebar should only need one button, the create new stage button, because all of the block code
the user makes can be created by pressing the buttons on the different 'command' objects.
not the most efficient method, but it was the only one that I could come up with given my limited knowlege of php */ ?>


<div class="sidenavL">
  <?php //header back to main ?>
  <a href="index.php">Back to main</a>
  <p>Blocks</p>
  <?php //the php code at the top should check which was the most recent post, and the first action of the user
  //will always be to create a stage command ?>
  <form method=POST>
  <button name="addStage" value="stageSelected" type="stageAddTrue">Add a 'Start Stage' Block</buttton>
  </form>
</div>

<div class="sidenavR">
  <p>Input Code</p>
  <?php //clicking this button should reset currentfullcode with the one inserted by the user
  //there is no safety check on user inserting text yet ?>
  <input type="text" name="InputString" placeholder="Insert pre-built code here">
  <button onclick="loadCheck()" name="submitInput" value="inputSubmitted" type="true" >Load Code</buttton></button>
  <p>My Code:</p>
  <?php //user can copy and paste this code somewhere for saving it, or just download it to the rpi. ?>
  <p><?php echo $_SESSION['currentfullcode']; ?></p>
  <button onclick="downloadCheck()" name="download Code" value="Downloaded" type="true" >Download Code to Makaniu</buttton>
  <script>
    function loadCheck() {
      confirm("Are you sure you want to load this code? Loading this code will replace the current program");
    }
    function downloadCheck() {
        confirm("Are you sure you want to download your program to the Makaniu?");
    }
  </script>

</div>

<div class="main">
  <h2>My Mission</h2>
<body>


<?php
    //it is at this point that each part of the array created by currentfullcode should be instantated as Commands
    //the layout variable should be found using the table in 'User Code String Translater', depending on the currentfullcode used to create the command
    //once instantated, they should use the display command function to


    class Command {
      //name - name of command user created, gets displayed
      private $name;
      //num - order in which this block currently is, appended to POST to locate where to add the next command in the order
      private $num;
      //custom string used to easily store what html the given block needs to display, key can be found in 'User Code String Translater'
      private $layout;
      //codestring that represents this specific command in the currentfullcode session variable
      private $codestring;

      function get_name() {
        return $this->name;
      }

      function get_num() {
        return $this->num;
      }

      function get_layout() {
        return $this->layout;
      }

      function get_codestring() {
        return $this->codestring;
      }

      function __construct($name, $num, $layout, $codestring) {
        $this->name=$name;
        $this->num=$num;
        $this->layout=$layout;
        $this->codestring=$codestring;
      }

      //This function takes the string layout and adds different parts of html together depending on the parameters
      //of the command.
      public function displayCommand() {
        $layoutArray = str_split($layout)
        //More than a div tag should be used in terms of styling thus part
        $command = '<div>';
        foreach($layoutArray as $char)
        {
          switch ($char) {
            case 'D':
            //button that deletes block
            $command .= '<form method="POST"><button name="delete'.$num.'" value=submit type=submit>x</button></form>';
            break;
            case 'N':
            //name of block
            $command .= '<p>'.$name.'</p>';
            break;
            case 'S':
            //Add chosen sensor from sensor options menu
            $command .= ';
            <form method="POST"><select name="sensorMenu"'.$num.'>
              <option>Time (absolute)</option>
              <option>Time (since start)</option>
              <option>Depth</option>
              <option>IMU</option>
              <option>Temperature</option>
              <option>Acceleration</option>
            </select></form>';
            break;
            case 'C':
            //Add chosen comparison from comparison menu
            $command .= ';
            <form method="POST"><select name="comparisonMenu"'.$num.'>
            <option>></option>
            <option>>=</option>
            <option>=</option>
            <option>IMU</option>
            <option>Temperature</option>
            <option>Acceleration</option>
            </select></form>';
            break;
            case 'X':
            //User input number w button to set
            $command .= '<form method="POST"><input name="usernum'.$num.'" type="number" placeholder="Number"></form>';
            break;
            case '{':
            //add if to block
            $command .= '<form method="POST"><button name="replaceBlockWIf'.$num.'" value=submit type=submit>+</button></form>';
            break;
            case '}':
            //remove if from block
            $command .= '<form method="POST"><button name="replaceBlockWoIf'.$num.'" value=submit type=submit>-</button></form>';
            break;
            case '[':
            //add end if block below this one
            $command .= '<form method="POST"><button name="addEndIf'.$num.'" value=submit type=submit>add "end stage if"</button></form>';
            break;
            case '(':
            //add else if block below this one
            $command .= '<form method="POST"><button name="addElseIf'.$num.'" value=submit type=submit>add "else if" block</button></form>';
            case ')':
            //add if block below this one
            $command .= '<form method="POST"><button name="addIf'.$num.'" value=submit type=submit>add "if" block</button></form>';
            break;
            case '+':
            //add chosen command block from menu below this block
            $command .= ';
            <form method="POST"><p>add block below: </p><select name="commandBlockMenu"'.$num.'>
            <option>Start Video</option>
            <option>Stop Video</option>
            <option>Record Video for x seconds</option>
            <option>Record Video for x minutes</option>
            <option>Record Video for x hours</option>
            <option>Start Time Lapse</option><option>Stop time Lapse</option>
            <option>Record Timelapse for n seconds</option>
            <option>Record Timelapse for n minutes</option>
            <option>Record Timelapse for n hours</option>
            <option>Take Picture</option>
            <option>Take Picture every n seconds</option>
            <option>Take Picture every n minutes</option>
            <option>Take Picture every n hours</option>
            </select><button name="addCom'.$num.'" value=submit type=submit>add</button></form>';
            break;
            case '*':
            //add chosen statement block from menu below this block
            $command .= ';
            <form method="POST"><p>add block below: </p><select name="statementBlockMenu"'.$num.'>
            <option>If</option>
            <option>While Not</option>
            <option>Record Video for x seconds</option>
            <option>Record Video for x minutes</option>
            <option>Record Video for x hours</option>
            <option>Start Time Lapse</option>
            <option>Stop time Lapse</option>
            <option>Record timelapse for n seconds</option>
            <option>Record timelapse for n minutes</option>
            <option>Record timelapse for n hours</option>
            <option>Take Picture</option>
            <option>Take Picture every n seconds</option>
            <option>Take Picture every n minutes</option>
            <option>Take picture every n hours</option>
            </select><button name="addCom'.$num.'" value=submit type=submit>add</button></form>';
            break;
            case 's':
            //add seconds to echo
            $command .= '<p>seconds</p>';
            break;
            case 'm':
            //add minutes to echo
            $command .= '<p>minutes</p>';
            break;
            case 'h':
            //add hours to echo
            $command .= '<p>hours</p>';
            break;
          }
          $command .= '</div>';
          echo $command;
        }

      }

    }
?>



</body>

</html>
