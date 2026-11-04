const fs=require('node:fs'),path=require('node:path');
const dir=path.resolve(__dirname,'../../output/function-audit-20261008');
const root='http://127.0.0.1:8000';
const results=[];
async function request(name,url,body,expected=200){
 const started=Date.now();
 try{
  let r;
  for(let attempt=0;attempt<3;attempt++){
    r=await fetch(root+url,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(45000)});
    if(r.status!==429)break;
    const retrySeconds=Number(r.headers.get('Retry-After'))||5;
    console.log('Rate limit; waiting',Math.min(retrySeconds,60),'seconds');
    await new Promise(resolve=>setTimeout(resolve,Math.min(retrySeconds,60)*1000+100));
  }
  const data=await r.json();
  results.push({name,url,http:r.status,status:r.status===expected?'passed':'failed',ms:Date.now()-started,detail:r.ok?undefined:JSON.stringify(data).slice(0,350)});
  console.log(name,r.status);
  return data;
 }catch(e){results.push({name,url,status:'failed',detail:e.message});return null;}
 finally{fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(path.join(dir,'api-results.json'),JSON.stringify(results,null,2));}
}
(async()=>{
 for(const p of ['/api/health','/api/metrics','/api/system_status','/api/dti/status','/api/dti/screening_libraries','/api/dti/clinical_targets'])await request(p,p);
 await request('双任务就绪门控','/api/ready',null,503);
 const drugs=await request('分子目录','/api/dti/drugs'),targets=await request('靶点目录','/api/dti/targets'),models=await request('模型目录','/api/dti/models');
 const drug=drugs.find(d=>d.name==='Dasatinib')||drugs[0],target=targets.find(t=>t.id==='ABL1')||targets[0];
 const pair={drug_smiles:drug.smiles,target_sequence:target.sequence};
 for(const m of models)await request('预测模型 '+m.id,'/api/dti/predict',{...pair,model_name:m.id});
 await request('批量DTI预测','/api/dti/predict_batch',{pairs:[pair]});
 await request('激酶谱分析','/api/dti/profile_panel',{drug_smiles:drug.smiles});
 await request('物理评分','/api/dti/biophysics_insights',pair);
 await request('ADMET','/api/dti/predict_admet',{drug_smiles:drug.smiles});
 await request('口袋结构','/api/dti/pocket_structure',{target_name:'ABL1',drug_name:'Dasatinib',drug_smiles:drug.smiles});
 const opt=await request('本地先导优化','/api/dti/optimize_lead',{...pair,target_name:'ABL1'});
 const candidates=opt?.candidates||[];
 await request('主动学习','/api/dti/active_learning',{target_sequence:target.sequence,target_name:'ABL1',candidates:[{name:drug.name,smiles:drug.smiles}]});
 if(opt?.baseline){
 await request('孔板规划','/api/dti/wetlab_dispatch',{target_name:'UI_TEST',baseline:opt.baseline,candidates});
 await request('报告生成','/api/dti/academic_report',{target_name:'UI_TEST',baseline:opt.baseline,candidates});
 await request('反馈模块空测量兼容性','/api/dti/wetlab_feedback',{target_name:'UI_TEST',candidates,measurements:[]});
 }
 await request('从头生成','/api/dti/de_novo_generate',{target_symbol:'ABL1',target_sequence:target.sequence});
 await request('逆合成','/api/dti/retrosynthesis_plan',{smiles:drug.smiles,molecule_name:'UI_TEST'});
 await request('虚拟筛选','/api/dti/virtual_screen',{target_symbol:'ABL1',target_sequence:target.sequence,max_hits:3});
 await request('错误SMILES拦截','/api/dti/predict',{...pair,drug_smiles:'invalid_smiles'},422);
 await request('错误模型拦截','/api/dti/predict',{...pair,model_name:'no_such_model'},422);
 await request('错误氨基酸序列拦截','/api/dti/predict',{...pair,target_sequence:'!!!!!!!!!!!!'},422);
 await request('缺失参数拦截','/api/dti/predict',{},422);
 const passed = results.filter(r => r.status === 'passed').length;
 const failed = results.filter(r => r.status === 'failed');
 console.log('SUMMARY', passed, '/', results.length);
 if (failed.length > 0) {
  console.error('API AUDIT FAILED:', failed);
  process.exitCode = 1;
 }
})().catch(e=>{console.error(e);process.exitCode=1});
