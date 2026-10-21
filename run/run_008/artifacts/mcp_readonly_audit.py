"""Use installed MCP v2 SDK to invoke only AbqJobPilot read-only tools."""
import asyncio,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; ABQ=Path(r'D:\Projects\abqjobpilot')
sys.path.insert(0,str(ABQ))
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
PROJECT=ROOT/'agenthub_sp_invopt'/'abqjobpilot_project'
JOB='SPIO_R008_Q200_N010_Candidate'
INP=ROOT/'run'/'run_008'/'artifacts'/'candidate_inp'/JOB/(JOB+'.inp')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
async def main():
    queue=PROJECT/'runtime'/'queue.json'; before=sha(queue)
    code=f"import sys; sys.path.insert(0, {str(ABQ)!r}); from abqjobpilot.mcp.server import main; raise SystemExit(main())"
    server=StdioServerParameters(command=sys.executable,args=['-c',code,'--project',str(PROJECT)])
    async with stdio_client(server) as (read,write):
        async with ClientSession(read,write) as session:
            init=await session.initialize(); listed=await session.list_tools()
            names=sorted(t.name for t in listed.tools)
            calls={}
            for name,args in [('abq_list_jobs',{'scope':'queue','limit':10}),('abq_list_jobs',{'scope':'history','limit':10}),('abq_job_status',{'scope':'queue','identifier':JOB}),('abq_locate_outputs',{'inp_path':str(INP)})]:
                r=await session.call_tool(name,args)
                key=name+':'+str(args.get('scope','outputs'))
                calls[key]={'is_error':getattr(r,'is_error',False),'structured_content':getattr(r,'structured_content',getattr(r,'structuredContent',None)),'content':[getattr(x,'text',str(x)) for x in r.content]}
    after=sha(queue)
    result={'mcp_sdk':'2.3.0','server_version':{'name':init.server_info.name,'version':init.server_info.version},'tools':names,'invoked_read_only_tools':list(calls),'calls':calls,'settings_dependent_tools':{'abq_preflight':'NOT_INVOKED_SETTINGS_UNKNOWN','abq_prepare_enqueue':'NOT_INVOKED_SETTINGS_UNKNOWN'},'queue_sha256_before':before,'queue_sha256_after':after,'queue_unchanged':before==after,'solver_started':False,'runner_started':False}
    out=ROOT/'run'/'run_008'/'artifacts'/'mcp_readonly_results.json'; out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': asyncio.run(main())
