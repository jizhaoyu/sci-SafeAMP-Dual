async (page) => {
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  const checks=[];
  await page.setViewportSize({width:1280,height:900});
  await page.goto('http://127.0.0.1:8017/');
  await page.getByRole('status').filter({hasText:'研究模型不可用'}).waitFor();
  await page.getByRole('button',{name:'运行双任务研究预测'}).click();
  await page.getByRole('alert').filter({hasText:'模型不可用'}).waitFor();
  checks.push('screening_503_visible');
  await page.getByRole('textbox').fill('AKX123INVALID');
  await page.getByRole('button',{name:'运行双任务研究预测'}).click();
  await page.getByRole('alert').waitFor();
  const invalid=await page.getByRole('alert').innerText();
  if(invalid.includes('模型不可用')) throw Error('Invalid input did not reach validation error');
  checks.push('invalid_sequence_rejected');
  for(const [route,label] of [['evolution','运行探索性突变排序'],['report','运行计算研究报告']]) {
    await page.goto('http://127.0.0.1:8017/'+route);
    await page.getByRole('button',{name:label}).click();
    await page.getByRole('alert').filter({hasText:'模型不可用'}).waitFor();
    checks.push(route+'_503_visible');
  }
  await page.goto('http://127.0.0.1:8017/wheel');
  await page.getByRole('button',{name:'导出高清 PNG'}).waitFor({state:'visible'});
  await page.waitForFunction(()=>document.querySelectorAll('main svg g').length===26);
  const labels=await page.locator('main svg g text').allTextContents();
  const positions=labels.filter(x=>/^\d+$/.test(x.trim())).map(Number);
  if(positions.length!==26||positions[0]!==1||positions[25]!==26)throw Error('Residue positions do not match source sequence');
  const distinct=await page.locator('main svg g circle').evaluateAll(nodes=>new Set(nodes.map(n=>n.getAttribute('cx')+','+n.getAttribute('cy'))).size);
  if(distinct!==26)throw Error('Projection contains overlapping residue centers');
  checks.push('wheel_26_residues_correct');
  await page.screenshot({path:'output/playwright/research-wheel.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.goto('http://127.0.0.1:8017/');
  await page.getByRole('status').filter({hasText:'研究模型不可用'}).waitFor();
  await page.screenshot({path:'output/playwright/research-mobile.png',fullPage:true});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
  if(overflow)throw Error('Mobile document overflows the viewport');
  checks.push('mobile_no_document_overflow');
  if(errors.length)throw Error(errors.join('; '));
  return {status:'passed',checks,page_errors:errors};
}
