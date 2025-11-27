typedef unsigned char uint8_t
typedef float		  float32_t
 
#define NOT_USED_MACRO (10)
 
typedef struct unused_tag
{
	char i;
	char i1;
}unused_tag_t;
 
uint8_t globalCnt;
uint8_t forCnt;
uint8_t g_global_local_same;
 
void switch_case_foo(uint8_t caseId)
{
	caseId = caseId + 1u;
	switch (caseId)
	{
		case 1u:
		globalCnt+=1u;
		case 2u:
		globalCnt+=2u;
		break;
	}
 
}
 
void for_foo(void)
{
	for (float32_t f = 0.0f; f < 2.0f ; f+= 0.1f)
	{
	globalCnt++;
	}
 
	for (uint8_t i = 0; i < 100u ; i++)
	{
		forCnt++;
		if(i = 5u)
		{
			i+=2u;
		}
	}
}
 
void not_hide_foo(void)
{
	uint8_t g_global_local_same = 20u;
	if (forCnt == 10u)
	{
		g_global_local_same++;
		forCnt = g_global_local_same;
	}
}