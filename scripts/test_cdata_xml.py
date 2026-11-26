import xml.etree.ElementTree as ET

xml_test = """<?xml version="1.0" encoding="UTF-8" ?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Test</title></head>
<body>
<script type="text/javascript">
//<![CDATA[
  var x = 10;
  if (x < 20) {
    var s = 'hello';
  }
//]]>
</script>
</body>
</html>"""

try:
    tree = ET.fromstring(xml_test)
    print("XML is strictly valid with //<![CDATA[! Root:", tree.tag)
except Exception as e:
    print("XML error:", e)
