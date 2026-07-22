/*
[이미지 HTML 추출 및 자동 매칭 엔진 - 멀티 링크 지원]
*/
function runImageExtractor(sheet) {
  // K3부터 가로로 10칸(K열~T열)의 링크 영역을 한 번에 읽어옵니다.
  var row3Values = sheet.getRange(3, 11, 1, 10).getValues()[0];
  var imgList = [];

  // 가로로 적힌 링크들을 순서대로 돌면서 이미지를 하나의 바구니에 모읍니다.
  for (var u = 0; u < row3Values.length; u++) {
    var url = row3Values[u].toString().trim();

    if (url && url.indexOf("dcinside") !== -1) {

      /*
       디시 본문 이미지 태그 파싱 내부 엔진 (Vultr 서버 사용)
      */
      var subList = [];

      try {

        var payload = {
          url: url
        };

        var options = {
          method: "post",
          contentType: "application/json",
          payload: JSON.stringify(payload),
          muteHttpExceptions: true
        };

        var response = UrlFetchApp.fetch(
          "http://64.176.232.213:5000/extract",
          options
        );

        var result = JSON.parse(response.getContentText());

        if (result.success && result.images && result.images.length > 0) {
          subList = result.images;
        } else {
          subList = ["본문 이미지 없음"];
        }

      } catch (e) {

        subList = ["연결 실패 : " + e.toString()];

      }

      if (subList.length > 0 && subList[0].indexOf("<img") !== -1) {
        imgList = imgList.concat(subList);
      }
    }
  }

  // 만약 모든 링크를 다 뒤졌는데도 이미지가 단 하나도 없다면 예외 처리
  if (imgList.length === 0) {
    imgList = ["본문 이미지 없음"];
  }

  var imgCnt = imgList.length;

  var startRow = 5;
  var lastRow = sheet.getLastRow();
  if (lastRow < startRow) lastRow = startRow;

  var numRows = lastRow - startRow + 1;

  var bValues = sheet.getRange(startRow, 2, numRows, 1).getValues();   // B열
  var kValues = sheet.getRange(startRow, 11, numRows, 1).getValues();  // K열

  // 결과 HTML이 출력될 열 번호 (J열)
  var targetColumn = 10;
  var outputValues = sheet.getRange(startRow, targetColumn, numRows, 1).getValues();

  // 기존 매칭 로직 그대로
  var validBCount = 0;

  for (var i = 0; i < numRows; i++) {

    var bCell = bValues[i][0];
    var kCell = kValues[i][0];

    if (bCell && bCell.toString().trim() !== "") {

      validBCount++;

      if (kCell && kCell.toString().trim() !== "" && validBCount <= imgCnt) {
        outputValues[i][0] = imgList[validBCount - 1];
      }
      else if (kCell && kCell.toString().trim() !== "") {
        outputValues[i][0] = "";
      }

    } else {

      if (kCell && kCell.toString().trim() !== "") {
        outputValues[i][0] = "";
      }

    }

  }

  sheet.getRange(startRow, targetColumn, numRows, 1).setValues(outputValues);
}
